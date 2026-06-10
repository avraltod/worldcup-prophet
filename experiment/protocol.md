# Daily Forecast Experiment — Pre-Registered Protocol

**Registered:** built June 7, 2026; locked at the June 11 kickoff after a final pre-kickoff review of squad news. This protocol governs evaluation only and may not be altered after June 11.

## Hypotheses (the model's own claims, falsifiable)

| # | Claim | Pre-registered value |
|---|---|---|
| H1 | Total group-stage points (3 exact / 2 result+GD / 1 result) | **72.0 expected** (72 matches × 1.00 avg) |
| H2 | Exact-score hits in group stage | **10.4 expected** (~1 in 7) |
| H3 | Correct outcomes in group stage | **44.0 expected** (61%) |
| H4 | Champion | Spain (26.8% — expected to FAIL in 73% of worlds; failure of this call alone does not falsify the model) |
| H5 | Calibration | Multiclass Brier score of outcome forecasts ≤ 0.60 (typical market-quality benchmark ~0.58–0.62) |

## The two parallel tracks

This experiment runs **two things at once**, and they must not be confused:

1. **The frozen entry** — the submitted picks never change. We grade them against reality (the scoring below). This measures *how good the locked pre-kickoff forecast was*.
2. **The living forecast** — after each result we re-condition the model (fix played matches, re-simulate the rest) and watch the probabilities move. This is the paper's main idea: **how a forecast updates as information arrives**. The baseline (pre-tournament 200k sim) is the prior at t=0; each match is an information gain.

## Daily procedure (after each matchday)

1. **Record** every final score (90-minute score for exact comparison; note ET/pens separately in knockouts).
2. **Update the living forecast**: `python3 scripts/record_update.py '{"group": {"<match#>": [hg,ag], ...}}' "label"` — re-conditions the model, logs each team's new champion/stage probabilities, the biggest movers, the **information content of the update in bits** (KL divergence vs the previous snapshot), AND a live **market snapshot** (Polymarket champion odds, de-vigged) so model and market are recorded side by side. Then `python3 scripts/plot_trajectory.py` and `python3 scripts/plot_market_compare.py` refresh the evolution + model-vs-market figures. (Knockout results: pass `{"ko": {"<match#>": "Winner"}}`.) Note: the market snapshot needs internet; if offline it logs `{}` and the model side still works.
3. **Score** each match: 3 / 2 / 1 / 0 points (exact / result+GD / result / wrong). Knockout matches score only if predicted matchup occurred.
4. **Compute per match:**
   - Points earned vs **EV points** (the model's own expectation for that match)
   - **Outcome surprise**: probability the model assigned to the realized outcome (flag < 15% as an upset)
   - **Scoreline surprise**: probability assigned to the realized exact score
   - **Brier contribution**: Σ(p_i − o_i)² over {H, D, A}
5. **Diagnose** every miss using the taxonomy below — name the failure mode, don't just narrate.
6. **Log**: append to `ledger.csv`, write the daily entry in `daily/`, update the Tournament Diary row in the dossier.

## Diagnosis taxonomy (what *really* went wrong)

| Code | Failure mode | Example | Model implication |
|---|---|---|---|
| **L** | Luck — low-probability event occurred, probabilities were sound | 75% favorite loses to a 90th-min deflection | None, unless L-codes cluster on one team |
| **S** | Scoreline miss, outcome right | predicted 1-0, actual 2-0 | None — modal picks hit ~1 in 7 by design |
| **P** | Probability misjudgment — evidence the input was wrong | "coin-flip" team wins 3-0 and dominates xG | Recalibrate mentally; note for 2030 model |
| **I** | Information gap — knowable fact the model lacked | star benched for rotation, model assumed full strength | Data-pipeline lesson, not model lesson |
| **B** | Bracket/structural — group order broke a knockout matchup | predicted K2 wins group | Quantify downstream dead entries |

**Discipline rule:** an upset is L until evidence (xG, dominance, repeated pattern) argues P. Resist narrating luck as error — and error as luck.

## Weekly rollup (every Sunday + post-group-stage)

- Cumulative points vs cumulative EV (the single headline: is the model beating its own expectation?)
- Running Brier vs H5 benchmark
- Exact-hit rate vs H2
- Bracket survival: % of knockout entries still alive vs simulation expectation
- Code tally: L/S/P/I/B counts — if **P** dominates, the model was miscalibrated; if **L/S** dominate, it ran as designed

## Endpoints

- **Primary:** total pool points vs H1, and pool rank (win/lose the bet)
- **Secondary:** H2–H5; post-tournament Brier decomposition; the killer-analysis hit rate (did eliminations follow C.2's predicted hazards?)
- **Output:** final "Reality vs Model" section appended to the academic paper after July 19 — the backtest the peer reviewers asked for, written by the tournament itself.
