# Revision Roadmap — Post-Tournament Pass

**Paper:** *Forecasting the 2026 FIFA World Cup: A Market-Calibrated Poisson–Elo Model and the Information Each Result Reveals*
**Decision from simulated panel review:** Reject (current form) → resubmit post-tournament. Major Revision gated on realized 2026 data.
**Target venue:** *Journal of Sports Analytics* (primary) or *JQAS*; MIT Sloan as alternative. arXiv/SSRN preprint now.

Each item is tagged: **[NOW]** = doable before/independent of the tournament · **[JUL]** = needs realized 2026 data (after July 19). Source reviewers in brackets: EIC, R1=methodology, R2=domain, R3=perspective, DA=devil's advocate.

---

## PART A — BLOCKING (must-fix; the decision hinges on these)

- [ ] **A1. Add the realized 2026 trajectory — the confirmatory study the paper promises.** **[JUL]** *(EIC C2, R1 C1, DA C1)*
  The headline forecast-evolution claim currently has *zero real data* — it is shown only on a simulated "dress rehearsal" (Fig. `fig_trajectory_demo`). After July 19, replace/augment with the actual match-by-match KL trajectory, plus the §4.8 model-vs-market resolution (whose forecast moved toward the other). This converts a deferred promise into a real confirmatory result and is the single change that makes the paper publishable.

- [ ] **A2. Add a NULL-MODEL comparison to defeat the tautology objection.** **[NOW]** *(DA C2, R3 m2)*
  "Information concentrates in the knockouts; the final ≈ 1 bit" is largely forced by tournament topology + the definition of KL — true even for a random forecast. Run the same information/pivotality pipeline on (i) a uniform-prior model and (ii) a random-results path, and show the *calibrated* model's pattern departs from the structural baseline (e.g., where the spikes land, the group-stage share, the model-vs-market divergence). Without this, the concentration result is a structural identity, not a finding.

- [ ] **A3. Re-anchor the information/pivotality framing in existing literature; reframe as application, not invention.** **[NOW]** *(EIC C1, R2 C1, R3 m4/m5, DA C2)*
  KL-per-result = the **logarithmic score** (Gneiting & Raftery 2007). "Pivotality" = **mutual information** *and* the **Leverage Index / win-probability-added** of the sabermetrics tradition (Lindsey 1963; Tango). Belief-path surprise = **Ely, Frankel & Kamenica (2015), *Suspense and Surprise***. Add a paragraph in §3.6 grounding eqs. (6)–(8) in these; change the abstract/title language from implying novel measures to "applying established information measures to a pre-registered live record."

- [ ] **A4. Report the live study under BOTH frozen-strength and strength-updating models.** **[NOW]** *(R1 C1)*
  The conditioning-only re-simulation freezes pre-tournament strengths, which mechanically suppresses group-stage information (a group result that *should* update a team's strength is scored ≈0 bits) and inflates "information arrives late." Run the trajectory under the in-tournament-updating model too (the §5.6 machinery already exists) and show the qualitative conclusions survive — or rename the metric "structural information conditional on frozen strengths." Pair with A1/A2.

---

## PART B — MAJOR (required for the revision bar)

- [ ] **B1. Soften every "validation" to "sanity check"; add proper calibration statistics.** **[NOW]** *(R1 C2, R2 m4, DA M1)*
  n=2 tournaments cannot validate. Add per-bin counts + binomial CIs to the reliability diagram; add a calibration test (Spiegelhalter z or calibration slope); benchmark Brier/RPS against the **market**, not a uniform baseline (Diebold–Mariano paired test on per-match differences); explicitly demote the n=2 champion comparison to "anecdotal."

- [ ] **B2. Promote slot-emergence to the headline; demote the scoreline-EV selector.** **[NOW]** *(EIC M3, R2 M3, R3 M2, DA M2)*
  Slot-emergence for the 48-team constrained third-place allocation is the genuine, format-specific novelty — quantify its value across *many* simulated 48-team brackets and pool structures, not three picks in one bracket. The scoreline-EV method scored *below* a naive 1-0-favorite on the backtest (68 vs 67; 52 vs 48), so right-size it to a methodological note.

- [ ] **B3. Trim the kitchen-sink.** **[NOW]** *(EIC M2, R3 M2, DA)*
  Cut the RF/XGBoost/SHAP appendix (C.3) to a paragraph and the xG section to a tight caveat; the surrogate explains variance in the author's *own simulation*, not reality. Remove unused figures left on disk. Tighten to the Poisson–Elo + slot-emergence + backtest spine.

- [ ] **B4. Add the Value-of-Information connection (highest-leverage positive addition).** **[NOW]** *(R3 M1)*
  Define pivotality on the *score* metric (how much resolving match m changes the optimal entry's expected points / pool-win probability), note that Appendix C.3 already estimates exactly this, and cite Howard (1966) and Raiffa & Schlaifer. This reframes a sports paper as a forecasting-methodology paper.

- [ ] **B5. Fix the Dixon–Coles test — test the decision, not the likelihood.** **[NOW]** *(R1 C3)*
  Re-run the optimizer *with* the DC correction and report how many of the 72 group picks change and the change in backtested points (DC reshuffles exactly the 0-0/1-0/0-1/1-1 cells the optimizer selects). If zero picks change, *that* is the clean justification; the 0.1% log-likelihood number is the wrong quantity.

- [ ] **B6. Re-de-vig with Shin and report pick changes.** **[NOW]** *(R1 M2, R2 m2)*
  The favorite–longshot bias Shin corrects is largest for the lopsided favorites whose 1-0 picks dominate the entry, so the "insensitive" dismissal is unverified. One-hour check: re-de-vig with Shin, report how many of 72 picks change.

- [ ] **B7. Report Poisson fitting diagnostics.** **[NOW]** *(R1 M1)*
  Report the fraction of fixtures where the λ-sum constraint binds, the mean H/D/A fitting residual, and a scoreline-frequency goodness-of-fit against historical WC data. Consider a soft penalty instead of the hard box.

- [ ] **B8. Fix the rotation-penalty overfitting exposure.** **[NOW]** *(R1 M3, DA M3)*
  The +2.7% is tuned on n=30 with a monotone-to-boundary response (an overfitting signature). Add leave-one-tournament-out CV (fit 2018, test 2022 and vice versa), a bootstrap CI on the Brier change, and report how many of the 30 games drive the effect. Present 120 Elo as illustrative.

- [ ] **B9. Add the missing literature; fix the orphan reference.** **[NOW]** *(R2 C1/M1/M2, R1 m1)* — see Part D.

- [ ] **B10. Differentiate explicitly from the bookmaker-consensus model.** **[NOW]** *(R2 C2)*
  Add a head-to-head paragraph vs Leitner/Zeileis/Hornik: what the method adds, and what it *gives up* (a single four-days-out snapshot vs a multi-book consensus with bias correction; Elo-for-knockouts vs market-implied abilities throughout).

- [ ] **B11. Correct the forecast-combination claim.** **[NOW]** *(R1 M4)*
  "Combination adds nothing because the sources are not independent" is a non-sequitur — convex combinations of correlated, differently-biased forecasts routinely beat both. State it as an empirical small-sample finding (or show the optimal held-out blend weight was 0/1); remove the incorrect theory.

- [ ] **B12. Separate the locked entry from the post-deadline recalibration.** **[NOW]** *(DA M6)*
  The §5.4 Group-K recalibration changed the most consequential bracket input after the original forecast. Present the originally-locked entry and the recalibration as two clearly-labeled objects; do not let the recalibration contaminate the "clean out-of-sample record" claim.

- [ ] **B13. Add a Generalization paragraph.** **[NOW]** *(R3 M3)*
  State the two abstract results: slot-emergence = a positional-loss decision rule (argmax-of-joint vs argmax-of-marginal); information-concentration = a property of *any* sequential-elimination process. Name 2–3 non-football instances (elections, seeded playoff pools, group-sequential clinical trials).

---

## PART C — MINOR (polish)

- [ ] **C1. Reconcile the champion number.** **[NOW]** State Spain pre-recalibration (27.4%) vs post (26.8%) once, at first use, and use consistently. *(EIC m1, R1 m6, DA m5)*
- [ ] **C2. State the pivotality MI precondition** (q_pre = Σ pₒ qₒ) and report the reconciliation residual within MC error. *(R1 M5)* **[NOW]**
- [ ] **C3. Tabulate the RPS values** actually used (currently claimed, never shown). *(R1 m2)* **[NOW]**
- [ ] **C4. Quantify the "market-calibrated" scope** — 24 matchday-3 fixtures use Elo, so the group stage is ~2/3 market-calibrated; say so in the abstract. *(R1 m3)* **[NOW]**
- [ ] **C5. Specify the third-place allocation matching algorithm** and tie/infeasibility resolution (the novel structural element). *(R1 m4)* **[NOW]**
- [ ] **C6. Confirm the group tiebreaker order** matches FIFA regulations (it drives slot emergence). *(R1 m5)* **[NOW]**
- [ ] **C7. Report bootstrap SEs on the KL/pivotality bits** (nonlinear, skewed; 0.014/0.11/0.99 need error bars). *(R1 m8)* **[NOW]**
- [ ] **C8. Extend the sensitivity sweep** to the draw constants (0.30, 700-decay) and add a small joint/Latin-hypercube perturbation, not only one-at-a-time. *(R1 M6)* **[NOW]**
- [ ] **C9. Add the KL-direction defensive sentence** and the caveat that pivotality inherits the model's miscalibration. *(R3 m1, m3)* **[NOW]**
- [ ] **C10. Footnote distinguishing "pivotality"** from the voting-theory term (Banzhaf/Shapley–Shubik power). *(R3 m5)* **[NOW]**
- [ ] **C11. Name the draw-realism finding** as a calibration-vs-discrimination / proper-scoring instance and cite the scoring-rule literature. *(R3 m4)* **[NOW]**
- [ ] **C12. Decompose backtest Brier** into reliability + resolution + uncertainty (Murphy decomposition) instead of the single "beats-uniform" number. *(R2 m4, R3)* **[NOW]**
- [ ] **C13. Remove unused figures** left on disk (`fig_germany`, `fig_usa`, `fig_uzbekistan`, `fig_title_runs`, `fig_group_difficulty`, etc.) or wire them in. *(EIC M2)* **[NOW]**
- [ ] **C14. Cite a fitted draw-model alternative** (Baker & McHale) where the hand-set Elo draw component is introduced. *(R2 m1)* **[NOW]**
- [ ] **C15. Deposit code + data in a timestamped public repo** (OSF/Zenodo/GitHub) — essential for the "locked before kickoff" claim to be verifiable. *(EIC m3, R1 m9)* **[NOW — the Monday commit covers this]**

---

## PART D — References to add (and one to fix)

| Reference | Why | For item |
|---|---|---|
| Gneiting & Raftery (2007), *Strictly Proper Scoring Rules*, JASA | The log-score family that KL-per-result belongs to | A3, C11 |
| Ely, Frankel & Kamenica (2015), *Suspense and Surprise*, JPE | Formalizes the belief-path surprise the evolution analysis re-derives | A3 |
| Leverage Index / WPA (Lindsey 1963; Tango et al.) | "Pivotality" is a named, decades-old quantity | A3 |
| Howard (1966), *Information Value Theory*; Raiffa & Schlaifer (1961) | Value-of-information framework | B4 |
| Koopman & Lit (2015), JRSS-A | Time-varying-strength state-space football model; relevant to the frozen-strength limitation | B9 |
| Constantinou & Fenton — pi-ratings (2013) and Dolores (2019) | Closest published ratings-driven tournament forecaster | B9 |
| Constantinou & Fenton (2012), RPS for football | Standard reference for the scoring rule the paper uses | B1, C3 |
| Groll et al. (2018) | Completes the WC-forecasting comparison set | B9 |
| Baker & McHale (time-varying ratings) | Fitted alternative to the hand-set draw component | C14 |
| **Karlis & Ntzoufras (2003)** | **In the bibliography but never cited — cite at the independence assumption (§3.2) or remove** | B9 |

---

## PART E — Sequencing

**Now (before June 11, for the arXiv/SSRN preprint):** the cheap, no-data fixes that improve the preprint and pre-empt the easy objections — A3 (reframe + cite), B9/Part D (references), B11 (fix combination claim), B12 (separate locked vs recalibrated), C1 (champion number), B1 language ("validation"→"sanity check"), C15 (deposit repo). An afternoon's work.

**The substantive no-data revisions (any time):** A2 (null model), A4 (dual-model trajectory), B2 (promote slot-emergence + multi-bracket simulation), B3 (trim), B4 (VoI), B5–B8 (DC / Shin / Poisson GOF / rotation CV), B10, B13, and the Part C statistics.

**After July 19 (the confirmatory pass):** A1 (realized trajectory + model-vs-market resolution) — then submit to *Journal of Sports Analytics*.

**One-line guidance the panel agreed on:** keep every honest negative result (they are the paper's credibility); the revision is about *re-billing* the two real contributions (slot-emergence, information-as-application) and *validating* them on real data — not about hiding weaknesses.
