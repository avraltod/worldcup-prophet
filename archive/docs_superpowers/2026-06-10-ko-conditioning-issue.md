# Issue: non-deterministic third-place slotting breaks KO conditioning

**Date:** 2026-06-10
**Status:** PREPPED 2026-06-11 — deterministic fix wired into `condition.py` + acceptance test
(`tests/test_ko_conditioning.py`); **awaiting the `REALIZED_THIRDS` fill from FIFA's announced
R32 bracket (~27 June)**. Confirmed baseline-neutral (see below).
**Severity:** Critical (corrupts the champion-probability trajectory — the paper's central metric)
**Discovered:** during the final review of the knockout-automation build (parked on branch
`ko-automation-parked`).

## Summary

When a **third-placed group team** plays in the Round of 32, recording that R32 result
(`record_update.py '{"ko": {"<m>": "<winner>"}}'`) **barely updates** the conditioned forecast.
The recorded winner is silently ignored in the majority of Monte-Carlo iterations, so the
champion / stage-probability trajectory under-responds to a real knockout result.

This is a **pre-existing issue in `scripts/condition.py`**, independent of the automation: the
manual "results update" protocol hits it too. The KO automation build merely surfaced it.

## Root cause

`condition.py`'s `conditional_probs` reconstructs the bracket **fresh inside every Monte-Carlo
iteration**. The third-place → R32 T-slot assignment is produced by `assign()` (a backtracking
solver over the `TS` eligibility table) which uses `random.shuffle` and is **not unique**:

```
# observed: condition.assign(<same 8 qualifying groups>) over 40 RNG seeds
distinct assignments: 21   (unique? False)
```

So across iterations, a given third-placed team is placed into many different T-slots. The
conditioning rule is:

```python
W[m] = ko_obs[m] if (m in ko_obs and ko_obs[m] in (a, b)) else simulate
```

For a T-slot match `m`, the recorded winner is `in (a, b)` only in the fraction of iterations
where that third-placed team happens to be assigned to slot `m`. Measured acceptance across the
8 T-slot R32 matches: **9.7%, 14.7%, 25.5%, 33.4%, 33.7%, 45.3%, 67.9%, 100%** — i.e. mostly
rejected and re-simulated.

The design assumption behind the KO resolver (`ko_bracket.py`) was that FIFA's third-place
table yields a **unique** assignment per set of 8 qualifying groups, so a single deterministic
choice (seeded) would match `condition.py`. That assumption is false for `condition.assign()`.

## Evidence of trajectory corruption

End-to-end, recording M79 = "Japan beats Czechia" (Japan = a third-placed team), N=8000:

| Team | QF prob before | QF prob after | Expected after a recorded R32 result |
|---|---|---|---|
| Czechia (loser) | 0.209 | 0.190 | ~0.0 (eliminated) |
| Japan (winner)  | 0.281 | 0.312 | ~1.0 (advanced to R16) |

The forecast hardly moves. The loser is not eliminated; the winner is not advanced.

## Scope

- **Affected:** recording a winner that is a **third-placed team in the Round of 32**
  (8 of the 32 R32 participants — a routine occurrence). Affects both the automation and the
  manual `record_update.py` path.
- **Not affected:** first/second-place R32 slots (deterministic), and **all of R16 → QF → SF →
  Final**, which key off recorded winner *names* via `R16/QF/SF` tables, not slots. Group-stage
  conditioning is unaffected.

## Why tests missed it

Every KO test recorded the *first-placed* team as the winner (slots `E1`,`I1`,`A1`,… are
deterministic), so `ko_obs[m] in (a, b)` was trivially satisfied. No test round-tripped a
**third-placed-team** R32 winner through `conditional_probs` to assert the conditioned
probability actually moved.

## Fix options (a methodology decision for the author)

1. **Deterministic FIFA third-place table.** Replace the random `assign()` with FIFA's official
   third-place combination table (a fixed lookup: set of 8 qualifying groups → unique slot
   assignment). Make both `condition.py` and `ko_bracket.py` use it. Once the group stage is
   fully observed, the bracket becomes deterministic and conditioning is exact.
   - Pros: correct; also improves the pre-tournament forecast (no spurious bracket randomness).
   - Cons: edits the paper's verified engine → needs re-verification; the official table must
     be sourced/encoded for the 2026 12-group / best-8-thirds format.
2. **Condition by round-membership for determined T-slots.** Change `condition.py` so a recorded
   T-slot winner is honored whenever that team is in the round, not only in the exact sampled
   slot. More invasive to the conditioning semantics; risk of subtle bracket inconsistencies.
3. **Leave KO conditioning as-is, document the limitation.** Accept that third-place R32 results
   under-update the trajectory. Not recommended — it silently distorts the paper's central metric.

Recommended: option 1, but it is a research/methodology call, not a mechanical fix.

## Required acceptance test when fixed

Record a third-placed-team R32 winner (e.g. M79) and assert, via `conditional_probs`:
- the loser's QF probability → ~0.0;
- the winner's QF probability → ~1.0.
This is the round-trip the current tests lack.

## Resolution prepped (2026-06-11)

Chose a hybrid of option 1: a **deterministic `assign()`** plus a pinned realized table,
rather than encoding all 495 group-combinations.

- `condition.py`: `assign()` now returns FIFA's official slotting via `REALIZED_THIRDS`
  when the qualifier set matches, and otherwise fills the 8 T-slots by **deterministic
  backtracking** (sorted candidates, no `random.shuffle`). `REALIZED_THIRDS = {}` is a
  placeholder to be filled from FIFA's announced R32 bracket (~27 June) — map each of the
  8 T-slot match numbers {74,77,79,80,81,82,85,87} to the GROUP whose third-placed team
  fills it.
- Added `realized_bracket(results)`: returns the slotting for fully-observed groups, used by
  the acceptance test and to read/cross-check the realized assignment on 27 June before pinning.
- `tests/test_ko_conditioning.py`: the doc's acceptance test (a recorded third-place R32
  winner reaches the R16 and eliminates its opponent) **plus** a baseline-unchanged guard.

**Baseline-neutral (measured).** Champion probabilities and third-place advance probabilities
are identical under random vs deterministic `assign()` to within Monte-Carlo noise (Spain ~27%,
Czechia advance ~68%, etc.), because champions are never third-placed teams and a team's
*advancement* depends on finishing top-8-among-thirds, not on which slot it fills. So the fix
does **not** alter the locked pre-registered baseline — the post-kickoff integrity concern does
not arise.

**Remaining for 27 June:** (1) read FIFA's official R32 bracket; (2) set `REALIZED_THIRDS` to the
8 slot→group assignments and cross-check against `realized_bracket(<final group results>)`;
(3) re-run `tests/test_ko_conditioning.py`; (4) un-park / rebase the KO automation branch and
apply the same `assign()` to `ko_bracket.py` before shipping it.

## State of the parked automation

The knockout automation is fully built and structurally tested (resolver, winner-flag parsing,
gate with hold-on-doubt + idempotency, orchestrator wiring, README subsection, integration
test) on branch **`ko-automation-parked`** (6 commits, `58c211b`…`5d3009c`). It is **not merged
to `main` and not pushed** — `main` matches `origin/main`, so the live group-stage workflow is
unaffected. The automation is correct as "record the winner under a consistent match number";
it is blocked only by this `condition.py` conditioning issue. Resolve the issue, then rebase /
re-validate the branch (including the acceptance test above) before shipping.
