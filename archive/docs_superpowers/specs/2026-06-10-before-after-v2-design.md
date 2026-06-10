# Before/After Forecast Records (v2) Design — worldcup-prophet

**Date:** 2026-06-10
**Author:** Avralt-Od Purevjav (Avraa)
**Status:** Approved, pending implementation plan
**Relationship:** Extends the live group-stage automation
(`archive/docs_superpowers/specs/2026-06-10-live-update-automation-design.md`, live on
`origin/main`). Built as an isolated **v2** that runs in parallel and is cut over only when
validated — the live v1 system is untouched until then.

## Purpose

Produce **two forecast records per match** instead of one: a **pre-game** record (~1hr before
kickoff, capturing the confirmed lineup and refreshed market) and a **post-game** record (after
the final whistle, applying the result and scoring performance). Over the tournament this yields
**104 × 2 = 208 records** (group stage 72×2 = 144 now; the knockout 64 are gated — see Scope).
The result is a finer-grained information trajectory that separates *where* information enters:
lineup/market drift before a match vs the result's information after it.

## Decisions (from brainstorming)

- **Pre-game record = snapshot + lineup + market.** The model's forecast is NOT changed at
  pre-game; the record logs the current conditioned forecast, the confirmed lineup, and the
  de-vigged market champion odds. No mid-experiment method change → preserves the
  pre-registration. (A lineup-driven model adjustment, e.g. the rotation layer, was rejected:
  it is unvalidated per the paper and would change the forecast method mid-experiment.)
- **Post-game record = result + re-conditioned forecast + performance** (points/Brier/EV gap),
  i.e. the existing per-result update, made per match.
- **Per-match records** (not per-matchday batch): simultaneous matchday-3 games each get their
  own pre and post record.
- **Phased rollout:** keep the live v1 system running so the pre-registration experiment starts
  cleanly; build v2 isolated, rehearse, cut over when validated.
- **Cadence:** GitHub Actions cron every 20 min (added only at cutover); 90-min pre-window.

## Architecture (parallel, isolated)

### New components

| File | Responsibility |
|---|---|
| `scripts/live_update_v2.py` | Polling orchestrator. Each run: fetch ESPN, decide per match whether a `pre` or `post` record is due, produce it, append to v2 files. Reuses `fetch_results`, `condition`, `market_snapshot`, and the `score_day` scoring logic. |
| `scripts/lineups.py` | Pure ESPN-lineup fetch+parse: `fetch_lineup(event_id, opener=urlopen)` → `{"home": [starters], "away": [starters]}` or `None` if not posted. |
| `.github/workflows/live-update-v2.yml` | The v2 workflow — created with **`workflow_dispatch` only (no cron)** so it is inert until cutover. |

### Isolation — separate files until cutover

v2 writes ONLY:
- `data/trajectory_v2.json` — the 208-record stream (pre + post entries).
- `data/results_log_v2.json` — results v2 has applied (its own, isolated from v1).
- `data/records_index_v2.json` — bookkeeping `{"pre": [match#...], "post": [match#...]}` for idempotency.

v2 does **not** touch `README.md` or any v1 file until cutover. The forecast math is unchanged
(same `condition.conditional_probs`); only the cadence, lineup fetch, trigger logic, and record
schema are new.

### Data sources (all public, no secrets)

- ESPN scoreboard (`soccer/fifa.world/scoreboard?dates=YYYYMMDD`) for fixtures, UTC kickoff,
  state, scores, winner flag, and `event.id`.
- ESPN summary (`soccer/fifa.world/summary?event=<id>`) → `rosters[].roster[]` with a `starter`
  boolean, for lineups.
- Polymarket gamma-api (via `market_snapshot.fetch_market_champion`) for the de-vigged market.

## Poll loop (one v2 run)

```
now = utcnow()
events = fetch ESPN scoreboard for today ±1 day
index  = load records_index_v2.json    # {"pre": [...], "post": [...]}
for event mapped to a GROUP match# m (via fetch_results.map_to_fixture):
    kickoff, state, final, scores, event_id = parse(event)
    if m not in index["pre"] and now < kickoff <= now + PRE_WINDOW(90 min):
        make_pre_record(m, event_id)     # snapshot forecast + lineup + market
    if m not in index["post"] and final and scores present:
        make_post_record(m)              # apply result -> re-condition + performance + market
commit v2 files if any record was written (github-actions[bot]; git pull --rebase before push)
```

- **Idempotency:** `records_index_v2.json` gates every record; created at most once; re-runs are
  safe no-ops.
- **PRE_WINDOW = 90 min** with ~20-min polling gives ~4 attempts before kickoff (absorbs cron
  delay). Lineups post ~60 min out; if not yet posted at record time, the pre still records with
  `lineup: null` (a pre is best-effort logging, never a hold).
- **POST** keeps the strict gate (state=post + completed + FT + integer scores + maps to a group
  fixture); on uncertainty it does not record and retries next poll.
- **v2 results log:** by the time `pre[k]` fires, all earlier finished matches have been posted,
  so `pre[k]`'s model forecast = forecast conditioned on all prior results (≈ `post[k-1]`); the
  pre's new content is the lineup + refreshed market.

## Record schema (`trajectory_v2.json` entry)

```json
{
  "phase": "pre",
  "match": 1,
  "label": "PRE M1 Mexico v South Africa",
  "time": "2026-06-11T18:05:00Z",
  "kickoff": "2026-06-11T19:00:00Z",
  "n_recorded": 0,
  "champion": {"Spain": 0.262, "Argentina": 0.181},
  "market_champion": {"Spain": 0.155, "Argentina": 0.142},
  "info_bits": 0.0,
  "lineup": {"home": ["..."], "away": ["..."]},
  "result": null,
  "performance": null
}
```

- `phase`: `"pre"` | `"post"`.
- `info_bits`: KL divergence of the champion distribution vs the **previous** record. So
  `pre[k]→post[k]` measures the result's information; `post[k-1]→pre[k]` measures model drift
  (≈0, since the model moves only on results) — a clean decomposition of where information enters.
- `lineup`: PRE only (`null` if not posted in time or for KO until unblocked).
- `result`: POST only — `[hg, ag]` for group, `"<winner>"` for KO (later).
- `performance`: POST only — `{points, ev_points, p_outcome, brier}` (group matches), computed
  with the **same 3/2/1 + Brier formulas** as `score_day` but written ONLY into the v2 record.
  v2 must NOT call `score_day.main()` (it appends v1's `experiment/ledger.csv`); the plan
  extracts the per-match scoring computation into a pure helper both can use, or reimplements
  the small formula inline — leaving `ledger.csv` untouched until cutover.

## Simultaneous matchday-3 games

Two matches kick off together → in one poll both pre-trigger (two pre records) and later both
post-trigger. Posts are processed in **match-number order**: `post[A]` applies A, re-conditions,
logs its marginal `info_bits`; then `post[B]` applies B on top, re-conditions, logs its marginal
`info_bits`. Each simultaneous game keeps its own pre and post record (no merging) — the 2×
count holds and overlap is handled, not assumed away.

## Cadence, secrets, guards

- **Cron** `*/20 * * * *`, added only at cutover; until then `workflow_dispatch` only.
- **Zero secrets:** ESPN + Polymarket are public; push uses the built-in `GITHUB_TOKEN`
  (`permissions: contents: write`).
- **Hard guards:** v2 may write ONLY its allowlist (`data/trajectory_v2.json`,
  `data/results_log_v2.json`, `data/records_index_v2.json`; `README.md` only post-cutover); a
  workflow allowlist check refuses to commit anything else; never the locked forecast files.
- **Commit identity:** `github-actions[bot]`. **Race safety:** `git pull --rebase` before push.

## Scope

- **Now:** group stage — 72×2 = 144 records.
- **Gated:** knockout post-records re-condition and are blocked by the third-place
  `condition.py` issue (`archive/docs_superpowers/2026-06-10-ko-conditioning-issue.md`). KO
  **pre**-records are snapshots and unaffected, but to avoid a half-built KO path, KO (pre and
  post) is added together once that issue is resolved. The full **208** is therefore gated on
  the KO conditioning fix.

## Cutover

1. Rehearse v2 via `workflow_dispatch` against live ESPN during the group stage; confirm sane
   pre/post entries in `trajectory_v2.json` and that no v1 file is touched.
2. At cutover, in one commit: add the `*/20` cron to `live-update-v2.yml`; remove the cron from
   the v1 daily workflow (single writer); wire the README `LIVE-RESULTS` block to
   `trajectory_v2.json`.
3. **Backfill caveat:** v2 records from cutover onward. Matches already played get no retroactive
   **pre** record (past lineups not cleanly available); their **post** results already live in
   v1. Phased-after-kickoff therefore means pre-records begin at cutover — noted explicitly in
   the data.

## Testing

- `lineups.py` parse — captured ESPN `summary.json` fixture (2022 final, event 633850) → starters
  extracted; `None` when rosters absent.
- **Trigger logic** as a pure `plan_records(events, index, now)` → list of `(match#, phase)`:
  pre fires only in-window and once; post only when final and once; idempotent re-run yields
  nothing; MD3 two-simultaneous yields two `pre` then two `post`.
- **Integration test:** fake event + seeded `results_log_v2` → a pre record (lineup+market+
  champion, no result applied) and a post record (result applied, performance computed);
  restores all v2 files in teardown.

## Out of scope / NOT doing

- No change to v1 or any v1 file before cutover. No lineup-driven model adjustment (rotation) —
  pre is a snapshot. No edits to `condition.py`. No KO records until the KO conditioning issue is
  resolved. No new secrets/deps (stdlib + existing repo code).
