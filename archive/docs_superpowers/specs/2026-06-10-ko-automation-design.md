# Knockout-Stage Automation Design — worldcup-prophet (Project B, fast-follow)

**Date:** 2026-06-10
**Author:** Avralt-Od Purevjav (Avraa)
**Status:** Approved, pending implementation plan
**Depends on:** the group-stage live-update automation
(`archive/docs_superpowers/specs/2026-06-10-live-update-automation-design.md`), which is
built and live. This spec extends that pipeline to the knockout stage (matches 73–104,
2026-06-28 onward).

## Purpose

Extend the daily, hands-off live-update pipeline so it also publishes **knockout** results:
map each finished KO match to its FIFA match number, record the advancing team, re-condition
the frozen forecast (so the champion-probability trajectory sharpens through the bracket),
and update the README — committed and pushed automatically, or held with an alert on any
uncertainty. The locked forecast never changes; only the outlook updates.

## Decisions (from brainstorming)

- **Scope:** record winners + trajectory (lean core, mirrors the group stage). For each KO
  match: map to match#, record the winner to `results_log["ko"]`, re-condition, update the
  README. **KO pool-points scoring of the bracket picks stays manual** (out of scope), as does
  diary prose / dossier / paper.
- **Winner source:** ESPN's per-competitor `winner: true` flag — correct through extra time
  and penalty shootouts; no detail-string parsing.
- **Bracket mapping:** a new deterministic resolver that **reuses `condition.py`'s bracket
  tables by import** (`R32`, `R16`, `QF`, `SF`, `TS`, `assign`, `GROUPS`, `ROW_MATCH`) and
  does **not** modify `condition.py` — the paper's verified engine stays untouched.
- **Hold-on-doubt** and the existing safety machinery (idempotency, allowlist, fail-loud
  alert) carry over unchanged.

## Architecture

### New component

| File | Responsibility |
|---|---|
| `scripts/ko_bracket.py` | Deterministic bracket resolver. `resolve_ko_pairings(results_log)` → `{match#: frozenset({teamA, teamB})}` for KO matches whose both teams are known. Computes final group standings from the 72 group results, applies the best-third assignment (reusing `condition.assign`/`condition.TS`), fills `condition.R32`, then propagates recorded KO winners through `R16`→`QF`→`SF`→final (104). Imports structural tables from `condition.py`; never modifies it. |

### Changes to existing files (small, additive)

| File | Change |
|---|---|
| `scripts/fetch_results.py` | Add `map_ko_event(parsed_match, results_log)` → `(match#, winner)` or `None`. Extend `eligible_targets` to also produce KO targets and apply the KO finality gate + iterative fixpoint resolution (below), returning `ko_targets = {match#: winner}` alongside the existing group `targets`/`scored`. |
| `scripts/live_update.py` | Build the combined `{"group": group_targets, "ko": ko_targets}` and pass it to `record_update.py` (which already merges both). Pass **group matches only** to `score_day.py`. No structural change to the gate→publish flow. |
| `scripts/render_readme.py` | Add a "Knockout results" subsection: for each recorded KO match, `M{n}: {winner} def. {loser}` (loser via `resolve_ko_pairings`). Champion model-vs-market table and the `X/104` count already update via `record_update`. |

Reused unchanged: `condition.py` (imported, not edited), `record_update.py`, `fixtures.py`,
`market_snapshot.py`, the GitHub Actions workflow, and the whole group-stage gate/allowlist.

### Data contracts (already established)

- `data/results_log.json` `"ko"` is `{"<match_no>": "<winning team>"}` for matches 73–104
  (string keys). `condition.conditional_probs` consumes it as
  `W[m] = ko_obs[m] if ko_obs[m] in (a, b) else simulate` — i.e. it self-validates a recorded
  winner against the two teams that actually reached that slot.
- ESPN scoreboard competitor carries `winner: true/false` (set on the advancer, including
  shootouts); `status.type` carries `state`/`completed` and a `detail` of `FT`/`AET`/`FT-Pens`.

## The resolver — `resolve_ko_pairings(results_log)`

Returns `{match#: frozenset({teamA, teamB})}` only for matches whose both teams are known.

1. **Guard:** if fewer than 72 group results are recorded, return `{}` (bracket not set).
2. **Standings:** per group A–L, compute pts/GD/GF from recorded results, sort →
   `grp1`, `grp2`, `third`. Rank the 12 thirds by pts/GD/GF; take the top 8.
3. **Third-place assignment:** `random.seed(2026)` (matching `condition.py`'s default) then
   `am = condition.assign(top8) or condition.assign(rk[:7] + [rk[8]])` using `condition.TS`.
   FIFA's table yields exactly one valid slot assignment per set of 8 qualifying groups, so
   `assign` returns that unique mapping deterministically. If `am is None` → leave those slots
   unresolved (→ hold downstream).
4. **R32 pairings:** fill `condition.R32` slots (`E1`, `A2`, `T74`, …) from `pos` + the
   assigned thirds; emit a pairing for each match whose both slots resolved.
5. **Later rounds:** propagate recorded KO winners through `condition.R16`→`QF`→`SF`→final
   (104 = winners of 101, 102). These need no standings — only `results_log["ko"]`.

Determinism note: the resolver depends on `condition.assign` returning a unique assignment;
a test asserts stability across seeds (see Testing).

## The KO gate — `map_ko_event` + `eligible_targets` extension

- **`map_ko_event(parsed_match, results_log)`** → `(match#, winner)` or `None`:
  winner = the competitor with `winner: true` (`fixtures.canon`-normalized); match# = the
  unique `m` with `resolve_ko_pairings()[m] == frozenset({canon(home), canon(away)})`.
  Zero or multiple matches → `None`.
- **KO finality (differs from group):** group matches require `detail == "FT"`; KO matches
  legitimately end FT/AET/FT-Pens, so KO finality is **flag-based**:
  `state == "post"` AND `completed is True` AND exactly one competitor has `winner: true`.
- **`eligible_targets` extension:** for each parsed ESPN event, first try the group-fixture
  path (unchanged). If it isn't a group fixture, treat it as a KO candidate. Resolve KO events
  **iteratively to a fixpoint**: into a working copy of the log, record every matured + final
  KO event that maps; re-resolve pairings (so a R32 winner recorded this batch unlocks its R16
  child); repeat until no new match maps. Then:
  - a **matured + final** KO event that still does **not** map → **HOLD + alert** (ambiguous
    standings or a missing prior result — never silently skipped);
  - a matured KO event that maps but is **not final** (no winner flag) → **HOLD**;
  - a match# already in `results_log["ko"]` → skip (idempotent);
  - KO events not yet matured (kickoff within 3h of now) → excluded silently.
  Output: `ko_targets = {"<match#>": winner}`. As in the group stage, any non-empty hold list
  causes the whole run to publish nothing and exit 1.

## Edge cases (all fail safe)

- **Exact standings tie** (identical pts/GD/GF for relevant positions): the slot is ambiguous,
  the affected R32 matches don't map → HOLD + alert for human resolution. The one acknowledged
  soft spot; fails safe.
- **`assign` no-solution:** strict top-8 fallback to `rk[:7] + [rk[8]]`; still none → HOLD.
- **Missing `winner` flag on a finished KO match** (ESPN data lag): not final → HOLD until
  populated.
- **R16 child before its R32 parent:** the iterative fixpoint records the parent first; if the
  parent is genuinely not yet final, the child holds.
- **Bronze final (match 103):** recorded for the README scoreboard only; not conditioned
  (consistent with `condition.py`, which uses only 104 for the champion). Its pairing is
  `(loser of 101, loser of 102)`.
- **KO team names:** a subset of the 48 group teams, all already verified to map by the
  group-stage name-mapping test — no new aliases.
- **Maturity:** ET + penalties finish < 3h from kickoff, so the existing 3h window holds; a
  pathological overrun just holds once and alerts.
- **score_day for KO:** not called for KO matches (it only scores group fixtures); `ledger.csv`
  receives group rows only.

## Testing

- **Resolver unit tests** against a synthetic complete 72-result fixture: assert the 16 R32
  pairings, the third-place assignment, and R16/QF/SF/final propagation from recorded winners.
- **`assign` determinism test:** identical pairings across multiple seeds (verifies the
  uniqueness assumption the design rests on).
- **Gate tests:** AET/pens event (winner flag) → final; no-winner → HOLD; ambiguous standings
  tie → HOLD; iterative fixpoint (R32 + its R16 child in one batch) → both recorded in order.
- **Integration test:** fake KO ESPN payload + a pre-seeded `results_log` (72 group results +
  needed prior winners) → asserts `ko` recorded, trajectory grows, README KO block updates;
  restores all mutated files in teardown.
- **No pre-tournament KO capture:** ESPN's KO bracket is empty until the group stage ends, so —
  unlike the group-stage name-mapping snapshot — real KO data cannot be captured now. The final
  task is a **rehearsal once R32 is set (~2026-06-28)** to validate against live data before
  relying on it.

## README changes

The existing `<!-- LIVE-RESULTS:START/END -->` block gains a **"Knockout results"**
subsection: for each recorded KO match, `M{n}: {winner} def. {loser}` (loser from
`resolve_ko_pairings`). KO score / shootout detail is omitted to keep `results_log`
winner-only as `condition.py` expects. The champion model-vs-market table and `X/104` count
already sharpen automatically as KO results condition the forecast.

## Out of scope

- KO pool-points scoring of the bracket picks (slot-emergence / advancement points) — manual.
- Diary prose, dossier regeneration, paper "Reality vs Model" — manual.
- Any change to the locked forecast/picks or to `condition.py`'s engine.

## Explicitly NOT doing

- No modification of `condition.py` (import its tables/functions only). No duplication of the
  bracket structure. No detail-string shootout parsing (use the `winner` flag). No partial-
  round publish (hold the run on any unresolved matured-final KO match). No new secrets or
  third-party deps.
