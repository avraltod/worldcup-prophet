# Editorial Decision — Simulated Peer Review

**Manuscript:** *Forecasting the 2026 FIFA World Cup: A Market-Calibrated Poisson–Elo Model and the Information Each Result Reveals*
**Panel:** EIC + Methodology (R1) + Domain (R2) + Perspective (R3) + Devil's Advocate (DA)
**Date:** 2026-06-09

## Decision: **MAJOR REVISION**

Three of five reviewers recommend Major Revision; Domain recommends Minor; the Devil's Advocate raised **two CRITICAL issues**, which preclude acceptance. The paper has a solid, defensible core — the slot-emergence decision layer and the pre-registered information design — but its newest component, the live two-track learning study (§4.9 + Appendix D), **overclaims what the evidence supports** and is the binding reason for the decision.

---

## The one thing to internalize

The reviewers split the paper cleanly into two halves:

- **The static forecast is strong.** Slot-emergence routing for the 48-team constrained allocation is, by unanimous agreement, the genuinely novel and defensible contribution; the Monte-Carlo error handling, the one-at-a-time sensitivity sweep, and the leakage policing are all praised; the pre-registration is called exemplary.
- **The learning study is the weakest part** — and it is precisely the part most recently added. Both R1 (Methodology, CRITICAL W7) and the DA (two CRITICALs) conclude that the "learning helps" result is presented as a validated, tuned, out-of-sample finding when it is in fact **in-sample, weakly identified, and effectively n≈2**. The paper already says, in prose, "a sanity check, not a validation" — the reviewers' core demand is to make the *headline, tables, and abstract* say the same thing.

This is not a rejection-level flaw; it is an over-claiming flaw, fixable by reframing plus a few new analyses.

---

## CRITICAL issues (block acceptance)

**C1 — In-sample tuning sold as out-of-sample validation (R1 W7, DA).** The learning rate `k` *and* the xG proxy are both calibrated on 2018+2022, and the learning result is then "validated" on 2018+2022. There is no held-out tournament. "2018 as a genuine out-of-sample test" is incorrect — 2018 is in the calibration set for both the proxy and the `k`-sweep.

**C2 — Effective sample size ≈ 2 for the central claim (R1 W7, DA).** `k` is tuned by champion log-loss on a *single realized champion per tournament* (n=1 outcome each, n=2 total). The two optima (40, 60) are individually unidentified; "interval 40–60, default 50" presents two noisy point estimates as a population range. The stress-test perturbations re-run the *same* 2022 data and cannot turn n=2 into evidence of a regularity.

---

## Consensus issues (all/most reviewers)

1. **Framing (EIC, all).** The paper reads as a prediction document — champion tables, 30 pages of group-by-group rationale — that buries its three real contributions. Lead with the decision/information science; move the prediction tables (Appendix A) to a non-peer-reviewed supplement.
2. **Affirmative framing ≠ hedged prose (DA, R1, R3).** The caveats live in prose ("sanity check," "cannot separate skill from luck") while the abstract, figures, and tables still assert "learning lifts the finalists, demonstrated." Align them.
3. **The xG proxy is unvalidated (R1 W5, DA).** `λ_obs = 0.326·SoT`, one coefficient, no held-out RMSE, and — despite the flow diagram listing "proxy-vs-real-xG agreement" as an output — no such diagnostic is shown. Report it.
4. **Differentiation from the dynamic/state-space literature (R2, DA).** The learning track is not distinguished from Koopman–Lit, Rue–Salvesen, Baker–McHale, or dynamic Elo — all of which already let strength evolve from performance. Either benchmark against them or argue precisely what is new (the xG signal? the regularization? the pre-registered live deployment?).
5. **Internal inconsistencies (DA, R1).** §4.9 reports Argentina at 16.9% (the k=60 value) while the tuning table's optimum is k=40 (19.0%) — read at whichever k tells the cleaner story. Also the de-vig fixture count is 24 in one place, 48 in another.
6. **The EV-scoreline contribution is near-null on realized data (R1 W3, EIC).** It lost to a naive "1–0 favorite" baseline on both backtest tournaments. Demote the claim *throughout*, not only in §4.9.

---

## Revision Roadmap (prioritized)

### P0 — must fix (unblocks the CRITICALs)
- **R-1. Reframe the learning study as exploratory / hypothesis-generating.** Remove "tuned," "two-tournament optimum," "near-optimal," "out-of-sample" language for `k`. State `k=50` is a weakly-identified default; the 2026 live run is the only validation. *(C1, C2)*
- **R-2. Add a fair control + a genuinely held-out test.** (a) A tuned-frozen or "static xG-favorite" baseline, so "learning beats frozen" is not just "a model with a free parameter beats one without." (b) Tune on one tournament, test on an unused one (2014, or a EURO). *(C1, C2)*
- **R-3. Validate the proxy.** Report the proxy's cross-validated RMSE and its agreement (correlation/bias) against scraped real xG on the matches where both exist — the diagnostic already in the pipeline. *(consensus 3)*

### P1 — important
- **R-4.** Restructure to lead with the decision/information science; relocate the group-by-group prediction tables to a supplement. *(EIC)*
- **R-5.** Align the abstract/figures/tables with the hedged prose. *(consensus 2)*
- **R-6.** Benchmark/situate the learning track against Koopman–Lit and dynamic-Elo; add missing references: Breiter–Carlin (1997), Rue–Salvesen (2000), Baker–McHale (2015), Groll et al. (2015), updated Zeileis bookmaker-consensus. *(R2)*
- **R-7.** Fix the k-value inconsistency in §4.9 (pick one k throughout) and the 24/48 de-vig fixture count; report de-vig/Dixon–Coles effects at the probability level, not the pick-count level. *(DA, R1 W1–W2)*
- **R-8.** Demote the EV-optimal scoreline claim throughout. *(R1 W3)*

### P2 — would elevate the paper
- **R-9.** Execute the information thesis the paper only gestures at: make the Ely–Frankel–Kamenica suspense/surprise mapping explicit; compute value-of-information (EVOI) for a few matches and contrast with champion-entropy pivotality; decompose the 2022 information gain into a result channel and a performance channel. *(R3 — the sharpest opportunity)*
- **R-10.** Sweep the regularization decay ρ and cap b (not just k); show the finalist-lift across the whole k range. *(R1 W6)*
- **R-11.** Formalize the pre-registration (timestamped registry) or reframe the 2026 run as prospective validation; clarify the Group-K post-build market recalibration. *(R3, DA)*

---

## Scores (0–100, illustrative)

| | Originality | Significance | Rigor | Stat. validity | Recommendation |
|---|---|---|---|---|---|
| EIC | 62 | 55 | — | — | Major |
| R1 Methodology | — | — | 74 | 58 | Major |
| R2 Domain | 63 (novelty) | — | — | — | Minor |
| R3 Perspective | 62 (concept) | — | — | — | Major |
| DA | — | — | — | — | (2× CRITICAL) |

## Code-correctness review (separate Opus pass over `scripts/`)

**Verdict: PASS — no correctness bugs.** The implementation faithfully computes the math in §3 and Appendix D; the 46-test suite is green; runs are deterministic; the headline tables (RMS residual 0.003, the k-sweep behaviour, the stress/robustness gaps) reproduce from the code to the decimal; `ev321.best_pick` matches all 72 locked picks. **Three minor cleanups** (do not affect any result): (1) a stale `modal_score`/`predict_groups.py` path that no longer generates the published predictions — regenerate through `ev321.best_pick` or delete it; (2) `optimality_check.py` uses a (3,1) rule in a comment, not the paper's 3/2/1 — under the correct rule the locked picks are 0/72 suboptimal; (3) add a code comment tying the Group-K `Portugal +66 / Colombia −67 / Netherlands −23` adjustments to the §3.13 postscript.

**Implication:** the Major-Revision issues are about *claims and framing*, **not** implementation. The math is right and reproducible — so every fix below is a writing/analysis task, not a debugging task.

## Revisions applied (v17 → v20)

**P0 — the two CRITICALs, answered with evidence (`scripts/heldout_validation.py`):**
- ✅ **R-1** §4.9 + App D.6/D.7 reframed as exploratory; `k=50` is "a weakly-identified default," not an "optimum"; numbers made consistent at k=50.
- ✅ **R-2** Leave-one-tournament-out CV added (train 2018→test 2022: +7.2 pts; reverse +1.8) — *out-of-sample*. Placebo control added (shuffled-xG lift collapses +6.8→−5.3) — it's the *signal*, not the parameter.
- ✅ **R-3** Proxy validated (coef stable 0.326/0.314; RMSE 0.99–1.09 beats naive 1.18–1.32).

**P1:**
- ✅ **R-5** Headline aligned with hedged prose.
- ✅ **R-6** Differentiation paragraph vs Koopman–Lit / Rue–Salvesen / Baker–McHale / Groll (App D.1) + 4 refs added & cited.
- ✅ **R-7** k-value inconsistency fixed (consistent k=50); 24/48 de-vig count reconciled.
- ◻ **R-8** EV-scoreline: demoted in §4.9; abstract frames it as the *objective* (acceptable) — not further demoted.

**P2:**
- ✅ **R-9 (partial)** Ely–Frankel–Kamenica formalization (pivotality=suspense, per-result KL=surprise) + KL-direction defense added (§3.6); result-vs-performance **channel decomposition** added (§4.9): result channel 1.52 bits, performance channel +0.26 bits beyond, correlation −0.09 (roughly orthogonal).
- ◻ **R-9 (remaining)** Full EVOI computation vs champion-entropy pivotality (the §5 score-metric distinction) not yet quantified.
- ◻ **R-10** ρ/b now flagged as a caveat in D.6; full sweep not run.
- ◻ **R-4 (big)** Restructure / move group tables to a supplement — deferred to pre-submission trim.
- ◻ **R-11** Pre-registration formalization — deferred.

Code cleanup: ✅ `condition.py` Group-K comment; ◻ `modal_score`/`optimality_check` cleanups deferred (cosmetic, no result impact).

## Bottom line

The static forecast — slot-emergence + the pre-registered information design — is publishable in a mid-tier applied-forecasting/sports-analytics venue after framing fixes. The learning study, as currently written, **overclaims**; reframed honestly as an exploratory pilot with a fair control, a held-out test, and a validated proxy, it becomes a sound companion rather than a liability. The code is sound; the decisive validation for all of it is the 2026 live run.
