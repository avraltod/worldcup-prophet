# Design: TECHNICAL_NOTES — the formula-level companion to the model

**Date:** 2026-06-11
**Status:** Approved in brainstorming (Option A: mirrored companion)
**Deliverables:** `TECHNICAL_NOTES.md` (repo root) + `TECHNICAL_NOTES.pdf`

## Purpose

A companion document to `HOW_THE_MODEL_WORKS.md` that tells the same pipeline story
in mathematical/statistical language: how raw information is converted into data
(measurement/encoding), and what mathematical and statistical operation each pipeline
step performs — definitions, formulas, distributions, estimators, and numerics — for
both the locked base model and Avraa's Prophet (the two-track self-learning forecaster).

Standalone from the paper. The 3/2/1 objective is treated as what it is: the
optimization target of an informal friends' pool.

This is also deliberately a capability test of Fable 5: the math must be written by
the main agent, verified line-for-line against the code.

## Non-goals

- Not a revision of the paper or of `HOW_THE_MODEL_WORKS.md`.
- Not developer documentation (no API docs, no install/run instructions).
- No new analysis, no new figures beyond what equations need.
- Does not touch the KO third-place conditioning fix (parked separately, awaiting
  the 27 June `REALIZED_THIRDS` fill).

## Core design decisions (settled with user)

1. **Scope:** both pipelines, one document. Part I = base model, Part II = Prophet.
2. **Format:** Markdown with GitHub-rendering LaTeX math, plus compiled PDF
   (pandoc → LaTeX), mirroring how `HOW_THE_MODEL_WORKS.md/.pdf` ships.
3. **Fidelity:** code-faithful. Every formula extracted from `scripts/` with actual
   locked constants. Pragmatic shortcuts documented as such.
4. **Structure:** mirrored companion — Part I section numbers align 1:1 with the six
   stages of `HOW_THE_MODEL_WORKS.md`, so the two documents can be read side by side.
5. **Anchors:** every displayed equation carries a code anchor
   `[file.py:function — constants as locked]`.
6. **Information→data emphasis (user request):** an explicit measurement/encoding
   treatment — how odds quotes, Elo tables, team news, fixtures, and ESPN box scores
   become numbers — plus the numerics at every step (grid resolutions, truncation,
   RNG seeding, sample sizes), not just the statistics.

## Document outline

**Part 0 — Notation and contract.** Teams $i$, ratings $R_i$, goal rates $\lambda$,
scoreline $(h,a)$, score function $S$. States the anchor contract and the honesty
rule: where code and clean math diverge, the note says so.

**Part I — The locked forecast (mirrors HOW_THE_MODEL_WORKS stages 0–6, same numbers):**

0. **The objective.** $S(\hat h,\hat a;h,a)\in\{0,1,2,3\}$; decision problem
   $(\hat h,\hat a)=\arg\max \mathbb{E}[S]$.
   Anchors: `scoring.py:score_match`, `ev321.py:ev_321/best_pick`.
1. **From information to numbers (inputs).** Measurement step for each input:
   odds quotes → implied probability vectors $1/o_i$; Elo tables → $R_i$;
   injury news → additive rating penalties; fixtures → bracket as directed graph.
   Anchor: `predict_groups.py:load_odds`, `fixtures.py`.
2. **De-vigging.** Overround, proportional-vig normalization
   $p_i=(1/o_i)/\sum_j(1/o_j)$ and what it assumes.
   Anchor: `predict_groups.py:load_odds`.
3. **Poisson goal model + scoreline choice.** Independent Poisson
   $P(h,a)=\mathrm{Pois}(h;\lambda_H)\,\mathrm{Pois}(a;\lambda_A)$; the inverse
   problem `fit_rates` solves (match W/D/L to fair probabilities; total goals
   grid-searched over $[1.6,3.4]$); expected-points pick vs modal score; why
   $\mathbb{E}[S]$ pulls toward 1-0 and 1-1; the realistic-scoreline revision layer
   as the operative pick rule.
   Anchors: `poisson_model.py:pois/outcome_probs/fit_rates/modal_score`,
   `realistic_scores.py:realistic/ko_realistic`.
4. **Monte Carlo simulation.** The 200k-tournament sampler: group score sampling,
   standings/tiebreakers, third-place assignment, Elo logistic
   $P(A\ \text{beats}\ B)=1/(1+10^{-(R_A-R_B)/400})$ for undrawn KO matchups.
   Anchors: `simulate.py:sample_score/simulate_group/assign_thirds/ko_winner`.
5. **Bracket optimization.** Advancement distributions → KO picks; slot value and
   pivotality as decision diagnostics.
   Anchors: `predict_knockout.py:probs/predict_pair`, `slot_value.py`, `pivotality.py`.
6. **ML risk check.** XGBoost risk model as validation layer: features, target, and
   what it does/doesn't change. Anchor: `ml_risk_xgb.py`.

**Part II — Avraa's Prophet (the self-learning model):**

7. **Measurement: match events → $\lambda_{obs}$.** ESPN box scores → shots-based xG
   proxy $\hat\lambda_{obs}=\beta_1\cdot\mathrm{SoT}+\beta_2\cdot\mathrm{otherShots}$
   ($\beta_1=0.326$, calibrated on 2018+2022); free-data constraint (no real WC xG);
   proxy validation (RMSE vs naive).
   Anchors: `performance.py:proxy_xg/compute_lambda_obs`, `calibrate_proxy.py:fit`.
8. **The expectation model.** $\lambda_{exp}$ as a function of rating difference via
   the fitted rate map (what the Frozen Prophet expects).
   Anchor: `learn.py:lambda_expected` (memoized on rounded rating diff).
9. **The learning update.** Net surprise
   $s=(\lambda_{obs}^{for}-\lambda_{exp}^{for})-(\lambda_{obs}^{against}-\lambda_{exp}^{against})$;
   regularized drift update $d\leftarrow\mathrm{clip}(\gamma d+ks,\pm 75)$ with
   $k=50$, $\gamma=0.95$; framed as a regularized-Elo/EFK-style filter; two-track
   design (Frozen $k=0$ control vs Learning treatment).
   Anchors: `learn.py:net_surprise/update_drift/LearningTrack`.
10. **Re-simulation and the trajectory.** Per-game conditioning + re-simulation under
    both tracks; N=4000 per snapshot, seed 2026.
    Anchors: `sim_tournament.py:simulate`, `replay.py:run_replay`.
11. **Information accounting.** Per-game $D_{KL}(p_t\|p_{t-1})$ in bits between
    consecutive champion distributions; result-vs-performance channel decomposition
    (1.52 vs 0.26 bits in the 2022 replay).
    Anchors: `snapshot.py:kl_divergence`, `replay.py:champion_dist`.
12. **How we know it works.** Leave-one-tournament-out CV, placebo (shuffled xG),
    k-sweep across two World Cups.
    Anchors: `heldout_validation.py`, `sweep_k.py`.

Each section: math first (definitions, formulas, distributional assumptions,
estimator), then a compact *"as implemented"* note pinning constants, numerics, and
shortcuts — flagged honestly where pragmatic rather than principled (e.g. $h\perp a$
independence, proportional-vig normalization).

## Production process

- Written by the main agent (Fable 5 test — no subagent drafts the math).
- **Read-before-write rule:** read each anchored function before writing its formula;
  every equation verified against code, not memory.
- Prose in Avraa's voice (`avraa-voice` calibration applies).
- PDF via pandoc → LaTeX.
- Estimated length: ~15–20 pages compiled.

## Verification

1. Anchor audit: final pass re-reading every anchor against its displayed equation.
2. Constants check: every numeric constant in the doc grepped back to source.
3. Spec/prose self-review: placeholders, contradictions, ambiguity.
4. PDF compiles and math renders on GitHub (spot-check).

## Error handling / risks

- **Code-vs-doc drift:** the realistic-scoreline revision and the v2 live pipeline
  are recent; sections 3 and 10 must describe the *current* operative code path, not
  the original one. Mitigated by the read-before-write rule.
- **KO conditioning issue:** section 10 should note the known third-place
  conditioning caveat and reference the parked fix, without depending on it.
