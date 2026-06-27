# Stage-2 conditional re-forecast ("Frozen 2") — pre-registration

**Frozen:** 2026-06-27, before any 2026 knockout result is observed (first
Round-of-32 match ~2026-06-29). This document fixes the *method* of the Stage-2
re-pick before the knockout phase begins, so the re-pick is a genuine second
freeze and not a hindsight-fit.

## Relationship to Frozen 1 (pre-registration integrity)

Frozen 1 — the pre-tournament, pre-registered forecast and the submitted entry
(tag `prereg-2026`) — is **unchanged** and remains the paper's immutable
pre-registration. Frozen 2 is a **separate** object: by design it conditions on
the *realized group stage* (look-ahead relative to Frozen 1), permitted because
the friends' pool allows a full knockout re-pick at the group→knockout boundary.
Frozen 2 is therefore **not** pre-tournament pre-registration; it is a method
freeze at the boundary. It does not modify Frozen 1, the paper's frozen forecast,
or the locked group-stage picks.

## Objective and scoring rule (the pool's, fixed)

Maximize expected pool points. Per knockout match the pool awards the **90-minute
regulation** score tier — 3 exact / 2 goal-difference / 1 correct result — **plus
+1** for the correctly predicted advancing team (max 4). Penalty/extra-time
*scores* are unscored; they only determine the advancer. The bracket is submitted
forward and a later pick scores **only if the projected matchup actually occurs**.

## Method (frozen)

1. **Ratings — Track B effective Elo:** live Elo + injury adjustments + lineup
   adjustments + the learned in-tournament drift; **no host bonus** (host edge is
   absorbed by the live ratings / drift). Learning-track hyperparameters, fixed
   and tuned only on 2018/2022 (never on 2026 knockout outcomes):
   **k = 50, decay = 0.95, bound = 75**.
2. **90' scoreline:** independent Poisson; means from Elo via `lambda_expected`
   (logistic win-expectancy → goals), goal-total band **(1.6, 3.4)**, grid cap
   **MAX_G = 8**; the EV-optimal scoreline maximizes the 3/2/1 tier. Independent
   Poisson (no Dixon-Coles); sensitivity check: 0/32 scoreline picks change for
   ρ ∈ {0.05, 0.10, 0.15}.
3. **Advancer cascade:** P(advance) = P(win 90') + P(draw 90')·[P(win ET) +
   P(draw ET)·q], extra-time means scaled to λ/3, penalty win prob **q = 0.5**
   (coin-flip; prior shootout records carry no predictive signal).
4. **Per-match pick:** argmax over (90' score, advancer) of
   [score-tier EV] + [P(advancer advances)]; a decisive 90' prediction forces the
   advancer, a draw frees it.
5. **Bracket:** the globally EV-optimal internally-consistent bracket by **exact
   dynamic programming** over the bracket tree (slot-occupancy estimated by Monte
   Carlo of the realized bracket; reach factorizes over the two disjoint feeding
   subtrees). The greedy per-match-myopic build is retained only as a baseline.
6. **Realized bracket input:** the official FIFA Round-of-32 slotting
   (`condition.REALIZED_THIRDS`, pinned at the group→KO cutover); Track B Elo
   computed from data available at the boundary.
7. **Scoreline readout (display):** the published 90' scoreline is the realistic
   rounded-expected-goals readout that Frozen 1 also uses
   (`realistic_scores.ko_realistic`): the advancer takes the higher rounded score,
   and a genuine toss-up stays level in regulation and is decided on penalties, so
   the entry shows real scorelines and penalty draws rather than the monotone
   points-optimal 1-0. This is **points-neutral** and does **not** change the
   optimization — the EV-optimal pick of item 4 remains the yardstick, and the
   advancer, the dynamic program, the champion, and every per-match EV are
   unchanged. *Amended 2026-06-27, before any 2026 knockout match.*

## Code provenance (pins the implementation)

- branch `ko-pool-repick` @ commit `572321777a6beb3f371edfbffb4c92290c782a81` (pushed to origin)
- SHA-256 `scripts/ko_match_ev.py` = `478529b93acd8d90f9fc8af188175149b60ada45caabb8fd3753a46a2895fe18`
- SHA-256 `scripts/ko_repick.py`  = `01139e63b579393bd74e91b1879808df12397d3878cff11477ec3dc73f25a4e3`
- *Readout amendment (item 7) supersedes the original freeze at commit `6beb5ca`
  / `ko_repick.py` `ee1dcf69…`; optimizer and all EVs unchanged.*

## Pre-specified analyses (reported after the knockout phase)

- Realized pool points of the Frozen-2 entry vs baselines: greedy, naive
  favourite-1-0, and the Frozen-1 pre-tournament knockout bracket.
- **Value of re-conditioning:** Frozen 2 (post-group) − Frozen 1 (pre-tournament)
  realized knockout points.
- Calibration: realized vs expected points.
- Full 2018/2022 backtest (32-team bracket adapter, post-group learned Elo, true
  90' scores) — the lean check (EV-optimal scorelines 33 vs naive 32 over both
  years) is superseded by this.

## Not changed by this freeze

Frozen 1; the paper's pre-registered living forecast and its Track A/Track B;
the locked group-stage picks; the submitted entry's group scorelines.
