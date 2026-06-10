# Live Update Automation Design — worldcup-prophet (Project B)

**Date:** 2026-06-10
**Author:** Avralt-Od Purevjav (Avraa)
**Status:** Approved, pending implementation plan
**Scope:** Project B of two. Project A (repo curation) is complete and pushed.
**Phase:** This spec covers GROUP-STAGE automation only. Knockout automation is a
deliberate fast-follow (separate spec) to be written during the group stage, before
the knockouts begin 2026-06-28.

## Purpose

During the 2026 World Cup (2026-06-11 – 2026-07-19), publish a daily, hands-off update
to the public pre-registration repo: fetch each completed match's final score, re-condition
the frozen forecast, score the day against the locked picks, and update the README
"Results tracking" section — committed and pushed automatically, with **no action from the
user**. If results cannot be obtained cleanly, publish nothing and alert.

The locked forecast never changes. Only the *outlook* (re-conditioned probabilities, the
trajectory, the scoreboard) updates.

## Decisions (from brainstorming)

- **Autonomy:** fully hands-off + auto-publish.
- **When unsure:** hold and alert — publish nothing that day, leave the repo untouched.
- **Publish scope:** lean public-results core only. Data files + README results section.
  Diary prose, dossier regeneration, and the paper stay manual / out of scope.
- **Mechanism:** dedicated orchestrator script run by **GitHub Actions cron** (not `/loop`,
  not a Claude cloud routine). The lean core is deterministic, so a script is more reliable,
  cheaper, and safer for a public pre-registration than an autonomous LLM; GitHub Actions
  runs in the cloud (no laptop) and already has push credentials.
- **KO:** group stage now; knockout resolution (winner + shootout + dynamic bracket) is a
  fast-follow spec.

## Architecture

### New components

| File | Responsibility |
|---|---|
| `scripts/fetch_results.py` | Pure data layer. Fetch fixtures + final scores from the ESPN public JSON scoreboard (`soccer/fifa.world`); normalize to `{matchno: [hg, ag]}` via `fixtures.canon`, carrying each match's UTC kickoff and finality status. No side effects; pure parse functions are unit-testable against captured JSON. |
| `scripts/live_update.py` | Orchestrator. Compute the matured-and-unprocessed target set, call `fetch_results`, run the confidence gate, and **only if clean** invoke the existing scripts and regenerate the README block. Supports `--dry-run`. |
| `.github/workflows/live-update.yml` | GitHub Actions cron. Checkout, install pinned deps, run `live_update.py`, commit + push if files changed, email on failure. |
| `requirements-live.txt` | Pinned deps for the workflow (`requests` only; everything else is stdlib + repo code). |

### Reused (unchanged) components

`scripts/condition.py` (conditional_probs), `scripts/record_update.py` (results_log +
trajectory + KL bits + market snapshot), `scripts/score_day.py` (ledger + points/Brier),
`scripts/fixtures.py` (GROUP_FIXTURES, canon), `scripts/market_snapshot.py`.

### Data contracts (already established by the reused scripts)

- `data/results_log.json`: `{"group": {matchno: [hg, ag]}, "ko": {matchno: winner}}`.
  Single source of truth for what has been processed.
- `record_update.py '<{"group": {...}}>' "<label>"`: merges into results_log, re-conditions,
  **appends** a snapshot to `data/trajectory.json` (label, n_played, info_bits, champion
  probs, market_champion, top_movers). NOTE: appends on every call → must be called at most
  once per matchday batch.
- `score_day.py '<[{home, away, hg, ag}, ...]>'`: appends `experiment/ledger.csv`.
- `fixtures.GROUP_FIXTURES`: list of `(row, group, home, away)`; `fixtures.canon` aliases
  team names.

### README integration

The "Results tracking" section carries machine-managed markers:

```
<!-- LIVE-RESULTS:START -->
... auto-generated: scoreboard of recorded matches, model-vs-market champion table,
    latest KL info_bits, top movers ...
<!-- LIVE-RESULTS:END -->
```

`live_update.py` replaces only the text between the markers. Missing or duplicated markers →
hold (do not guess).

### Data flow (one daily run)

```
GitHub Actions cron (13:00 UTC)
 → live_update.py
    1. fetch_results.py: pull ESPN scoreboard over a window of recent dates;
       each event carries UTC kickoff + finality. target =
       { ESPN events that are FINAL and matured (kickoff > 3h ago) and map to
       a GROUP fixture } − { match#s already in results_log.json }
    2. confidence gate (below). Fail → exit 1, no writes → Actions emails. STOP.
    3. clean → record_update.py '<{"group": {...}}>' "Matchday N, <date>"
             → score_day.py '<[{home, away, hg, ag}, ...]>'
    4. regenerate README LIVE-RESULTS block from trajectory.json latest snapshot
 → workflow: if files changed → commit "Live update: <date> (matchday N)" + push; else no-op
```

## Safety gate

A day's batch publishes **only if every check passes**. Any failure → log the reason,
exit non-zero, write nothing → GitHub Actions emails the user.

1. **Strict finality** — a match is eligible only if ESPN reports `status.type.state == "post"`
   **and** `status.type.completed == true` **and** `status.type.detail == "FT"` (plain
   full-time; group matches never go to ET/pens, so `AET`/`FT-Pens` details are out-of-scope
   knockouts and are ignored) **and** both competitors carry an integer score. Anything else →
   the match is simply not in the target set (not a hold).
2. **Completeness within a matchday** — when at least one match of a given calendar matchday is
   eligible, every *matured* match (kickoff > 3h ago) of that same matchday must also be
   eligible; if a sibling match is matured but not yet `FT`, **hold the whole matchday** (keeps
   per-batch KL `info_bits` honest). Matches not yet matured are excluded silently.
3. **Sanity bounds** — scores are integers 0–19; both team names map via `fixtures.canon` to a
   single GROUP fixture. Unmapped name, or a pairing that isn't a known group fixture → hold
   (catches wrong-tournament / renamed-team / knockout fetches).
4. **No-op detection** — if the target set is empty (rest day or already processed), exit 0
   cleanly: no commit, no trajectory entry.

Single-source note: per the source decision, ESPN is the **only** feed. The strict-finality
and sanity checks (plus every update being a small, human-visible public commit) are the
safeguards in place of cross-source agreement.

### Idempotency

- `results_log.json` is the sole record of processed matches; the orchestrator acts only on
  matches not already in it.
- Because `record_update.py` appends a trajectory snapshot per call, a double-run must be
  prevented: a re-run on an already-processed day hits check #4 and exits without calling
  `record_update.py`. Outcome: safely re-runnable; at most one trajectory snapshot per
  matchday.
- **Missed-run recovery is automatic:** the target set is "all matured, unprocessed matches,"
  so a skipped/failed day is swept up by the next run. No catch-up logic.

### Hard guards (pre-registration protection)

- The orchestrator may write **only** to this allowlist:
  `data/results_log.json`, `data/trajectory.json`, `experiment/ledger.csv`,
  `README.md` (LIVE-RESULTS block only).
- It never touches locked files (`Avraa_Prediction_WC2026.*`, `data/group_predictions*.json`,
  the entry, the paper).
- Enforcement is belt-and-suspenders: an allowlist check in the script **and** a workflow
  step that asserts `git diff --cached --name-only` ⊆ allowlist before committing; otherwise
  abort the commit and fail (alert).

## Scheduling, secrets, permissions

- **Cron:** once daily at **13:00 UTC**. Target set is maturity-based (kickoff > 3h ago), so
  the exact cron time is not critical and matchday/UTC-boundary crossings don't cause false
  holds.
- **Concurrency:** a workflow `concurrency` group prevents overlapping runs.
- **Kickoff time:** taken directly from ESPN's `event.date` (ISO-8601 UTC, e.g.
  `"2026-06-11T19:00Z"`). No `schedule_ub.json` timezone inference needed — the maturity test
  compares ESPN's UTC kickoff against `now − 3h`.
- **Push:** built-in `GITHUB_TOKEN` with `permissions: contents: write`. No PAT.
- **Data sources:** ESPN public JSON scoreboard (scores + UTC kickoff) and Polymarket
  gamma-api (market champion, via the reused `market_snapshot.py`) are both public, no API key
  → the pipeline needs **zero secrets**.
- **Commit identity:** `github-actions[bot]`, so automated updates are visually distinct from
  locked human commits. Message: `Live update: <date> (matchday N)`.
- **Deps:** pinned in `requirements-live.txt` for reproducible Actions builds.

## Testing

- `fetch_results.py` + the validation logic are pure → unit tests with fixtures:
  clean matchday, missing match, source disagreement, unmapped team, rest day (empty target).
- `live_update.py --dry-run`: full pipeline except commit/push, for local rehearsal before
  kickoff.
- Existing `tests/` and `pytest.ini` conventions are followed.

## Out of scope (this spec)

- Knockout-stage automation (winner resolution, shootout parsing, dynamic bracket mapping) —
  separate fast-follow spec before 2026-06-28.
- Diary prose (`experiment/daily/*.md`), dossier regeneration (`make_paper.py`), weekly
  rollups, and the paper "Reality vs Model" section — remain manual.
- Any change to the locked forecast or picks — forbidden by design.

## Explicitly NOT doing

- No `/loop` (requires a live session/laptop). No Claude cloud routine for the core (LLM
  nondeterminism on a public pre-registration; MCP tools may be absent headless). No secrets
  storage. No edits to locked files. No partial-matchday publishes.
