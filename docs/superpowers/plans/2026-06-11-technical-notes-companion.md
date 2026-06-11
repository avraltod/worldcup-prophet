# TECHNICAL_NOTES Companion Document Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **EXECUTION CONSTRAINT (from spec):** The document's math and prose MUST be written by the main agent (this is a deliberate Fable 5 capability test). Do NOT dispatch subagents to draft sections. Subagents may only be used for read-only verification if needed.

**Goal:** Write `TECHNICAL_NOTES.md` + `TECHNICAL_NOTES.pdf` — the formula-level companion to `HOW_THE_MODEL_WORKS.md` covering both the locked base model (Part I, §0–6) and Avraa's Prophet (Part II, §7–12), code-faithful with anchors.

**Architecture:** One Markdown document at repo root, section numbers mirroring `HOW_THE_MODEL_WORKS.md` stages 0–6, then Prophet sections 7–12. Every displayed equation carries an anchor `[file.py:function — constants]`. PDF compiled with pandoc + tectonic. Built section by section, one commit each, with a read-before-write rule: read the anchored code immediately before writing its formulas.

**Tech Stack:** Markdown with LaTeX math (GitHub-rendering `$...$`/`$$...$$`), pandoc, tectonic (`pandoc TECHNICAL_NOTES.md -o TECHNICAL_NOTES.pdf --pdf-engine=tectonic`).

**Spec:** `docs/superpowers/specs/2026-06-11-technical-notes-companion-design.md`

**Universal rules for every section task (apply silently in each task below):**

1. **Read-before-write:** Read the listed anchor files/functions IN FULL immediately before writing the section. The formulas given in this plan are the *expected* shape from the spec; if the code differs, **the code wins** and the section (and, if needed, a note in the doc) reflects the code.
2. **Section template:** math first (definitions, formulas, assumptions, estimator), then a compact **"As implemented"** block pinning constants, numerics (grid resolutions, truncation, RNG, sample sizes), and pragmatic shortcuts flagged honestly.
3. **Anchor format:** every displayed equation block is followed by a line like
   `*Anchor: `scripts/poisson_model.py:fit_rates` — total-goals grid [1.6, 3.4].*`
4. **Voice:** Avraa's voice per the `avraa-voice` skill — apply it when drafting prose.
5. **Compile check after each section:** run
   `pandoc TECHNICAL_NOTES.md -o /tmp/tn_check.pdf --pdf-engine=tectonic`
   Expected: exit 0, no LaTeX math errors. (This is the "test" of each task.)
6. **Commit only `TECHNICAL_NOTES.md`** (plus `TECHNICAL_NOTES.pdf` in the final task). Never `git add -A` — the worktree carries unrelated in-progress KO-fix edits (`scripts/condition.py`, `tests/test_ko_conditioning.py`, `archive/docs_superpowers/2026-06-10-ko-conditioning-issue.md`) that must NOT be committed by this plan.

---

### Task 1: Document skeleton + Part 0 (notation and contract)

**Files:**
- Create: `TECHNICAL_NOTES.md`
- Read first: `HOW_THE_MODEL_WORKS.md` (full, to mirror its stage titles and numbering)

- [ ] **Step 1: Read `HOW_THE_MODEL_WORKS.md` in full.** Note its exact stage titles 0–6; Part I section titles must visibly correspond.

- [ ] **Step 2: Create `TECHNICAL_NOTES.md`** with:
  - Title: `# Technical Notes: The Model in Formulas` + subtitle: *"The companion in formulas — every pipeline step as the mathematics it implements. Reads side-by-side with HOW_THE_MODEL_WORKS.md."*
  - **Part 0 — Notation and contract**, defining: teams $i$; Elo ratings $R_i$; goal rates $\lambda_H, \lambda_A$; scoreline $(h,a) \in \mathbb{Z}_{\ge0}^2$; predicted scoreline $(\hat h,\hat a)$; pool score function $S(\hat h,\hat a; h,a) \in \{0,1,2,3\}$; probability vectors $p$; champion distribution $p_t$ after game $t$. State the two contracts: (a) every displayed equation carries a code anchor with locked constants; (b) honesty rule — where the code is a pragmatic shortcut rather than clean math, the note says so explicitly.
  - Empty section headers for §0–§6 (Part I, titles mirroring HOW_THE_MODEL_WORKS) and §7–§12 (Part II — Avraa's Prophet) using the titles from the spec, each with a one-line *"(section pending)"* placeholder that later tasks replace.

- [ ] **Step 3: Compile check.** Run `pandoc TECHNICAL_NOTES.md -o /tmp/tn_check.pdf --pdf-engine=tectonic`. Expected: exit 0, PDF produced.

- [ ] **Step 4: Commit.**
  ```bash
  git add TECHNICAL_NOTES.md
  git commit -m "Start TECHNICAL_NOTES: skeleton, notation, anchor contract"
  ```

### Task 2: §0 The objective — 3/2/1 scoring as a decision problem

**Files:**
- Modify: `TECHNICAL_NOTES.md` (§0)
- Read first: `scripts/scoring.py` (full), `scripts/ev321.py` (full)

- [ ] **Step 1: Read `scripts/scoring.py` and `scripts/ev321.py` in full.**

- [ ] **Step 2: Write §0.** Required content:
  - $S$ as a piecewise function: 3 if $(\hat h,\hat a)=(h,a)$; 2 if same outcome and $\hat h-\hat a = h-a$; 1 if same outcome (sign of $h-a$); 0 otherwise. Verify the exact tier conditions against `scoring.py:_outcome/score_match`.
  - The decision problem: $(\hat h,\hat a) = \arg\max_{(\hat h,\hat a)} \mathbb{E}_{(h,a)\sim P}\,[S(\hat h,\hat a;h,a)]$ where $P$ is the match's scoreline distribution — and how `ev321.py:ev_321` computes the expectation (the summation domain / goal truncation used in the code) and `best_pick` the argmax (its search grid).
  - Why this objective differs from "pick the most likely result," with the 1-1-on-draws argument stated formally: all draws share $h-a=0$, so $\mathbb{E}[S \mid \text{predict } 1\text{-}1] \ge 2\,P(\text{draw})$ plus the exact-hit bonus.
  - "As implemented" block + anchors.

- [ ] **Step 3: Compile check** (universal rule 5).

- [ ] **Step 4: Commit:** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES §0: the 3/2/1 objective as a decision problem"`

### Task 3: §1 From information to numbers (inputs)

**Files:**
- Modify: `TECHNICAL_NOTES.md` (§1)
- Read first: `scripts/predict_groups.py` (full), `scripts/fixtures.py` (full), plus the actual input data files they load under `data/` (open each one referenced by the loaders; list their fields)

- [ ] **Step 1: Read the loaders and the data files they reference.** Identify for each input the raw form → numeric encoding.

- [ ] **Step 2: Write §1.** Required content — the measurement map for each of the four inputs (this is the user's explicit "information → data" request):
  - Odds quotes: decimal odds $o_j$ per outcome $j\in\{H,D,A\}$ → implied probabilities $1/o_j$ (de-vigging deferred to §2); which books/markets enter and how multiple sources are combined (read the code; document the actual rule, e.g. median/mean/single source).
  - Elo table: published rating → $R_i$ (state the source and the date of collection, June 5–7 2026, per HOW_THE_MODEL_WORKS §1).
  - Team news: confirmed absence → additive rating penalty $R_i \leftarrow R_i - \delta$; document the actual $\delta$ values used in the code/data.
  - Tournament structure: 104 fixtures + advancement rules encoded as a directed graph / fixture list; note the 8-of-12 third-place rule as a combinatorial feature of the structure (formalized in §4).
  - "As implemented" block + anchors (`predict_groups.py:load_odds`, `fixtures.py`, exact data file paths).

- [ ] **Step 3: Compile check.**

- [ ] **Step 4: Commit:** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES §1: information-to-numbers measurement maps"`

### Task 4: §2 De-vigging — prices to fair probabilities

**Files:**
- Modify: `TECHNICAL_NOTES.md` (§2)
- Read first: `scripts/predict_groups.py:load_odds` (re-read the normalization lines)

- [ ] **Step 1: Re-read the normalization code.**

- [ ] **Step 2: Write §2.** Required content:
  - Overround $V = \sum_j 1/o_j - 1 > 0$; proportional normalization $p_j = \dfrac{1/o_j}{\sum_k 1/o_k}$.
  - What proportional de-vigging assumes (vig spread proportionally across outcomes) and the known alternative it ignores (favorite–longshot bias / power methods) — one short honest paragraph, flagged per the honesty rule.
  - Worked numeric example consistent with HOW_THE_MODEL_WORKS §2 (50/30/28 → 46/28/26).
  - "As implemented" block + anchor.

- [ ] **Step 3: Compile check.**

- [ ] **Step 4: Commit:** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES §2: de-vigging math"`

### Task 5: §3 Poisson goal model and scoreline choice

**Files:**
- Modify: `TECHNICAL_NOTES.md` (§3)
- Read first: `scripts/poisson_model.py` (full), `scripts/realistic_scores.py` (full)

- [ ] **Step 1: Read both files in full.** `realistic_scores.py` is the operative pick rule after the 2026-06-10 realistic-scoreline revision (commit `a23a138`) — the section must describe the CURRENT pick path, with the pure $\arg\max \mathbb{E}[S]$ as its foundation.

- [ ] **Step 2: Write §3.** Required content:
  - Model: $P(h,a) = \mathrm{Pois}(h;\lambda_H)\,\mathrm{Pois}(a;\lambda_A)$ with $h \perp a$; honesty note that real scorelines show small negative/positive dependence (bivariate Poisson exists; the code uses independence — say so).
  - The inverse problem `fit_rates` solves: given fair $(p_H, p_D, p_A)$, find $(\lambda_H,\lambda_A)$ s.t. the implied outcome probabilities match; parameterized by total goals $T=\lambda_H+\lambda_A$ grid-searched over $[1.6, 3.4]$ (read the code for grid step and the objective minimized — document exactly).
  - `outcome_probs`: the summation $P(\text{home win}) = \sum_{h>a} P(h,a)$ etc., with the actual goal truncation bound from the code.
  - Pick rules: `modal_score` (the argmax of $P(h,a)$) vs the $\mathbb{E}[S]$-optimal pick (from §0) vs the realistic-scoreline layer `realistic/ko_realistic` — give each as a formula/decision rule and state which one produces the published picks.
  - Why $\mathbb{E}[S]$ pulls toward 1-0 and 1-1 (margin tier dominates exact tier for plausible $\lambda$'s — show the comparison inequality on a worked example).
  - "As implemented" block + anchors.

- [ ] **Step 3: Compile check.**

- [ ] **Step 4: Commit:** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES §3: Poisson model, fit_rates inverse problem, pick rules"`

### Task 6: §4 Monte Carlo tournament simulation

**Files:**
- Modify: `TECHNICAL_NOTES.md` (§4)
- Read first: `scripts/simulate.py` (full, 270 lines)

- [ ] **Step 1: Read `scripts/simulate.py` in full.** Confirm the simulation count (HOW_THE_MODEL_WORKS says 200,000), tiebreaker order, third-place assignment logic, and the late-tournament rating variant in `ko_rating(team, late=...)`.

- [ ] **Step 2: Write §4.** Required content:
  - The estimand: advancement/champion probabilities as expectations over tournament realizations, estimated by MC with $N$ draws; MC standard error $\approx \sqrt{p(1-p)/N}$ evaluated at the locked $N$.
  - Group stage: scoreline sampling (`sample_score` — document the sampler: Poisson draws at fitted $\lambda$'s, plus any truncation), standings computation with the exact tiebreaker sequence from the code.
  - Third-place qualification: `assign_thirds` — the ranking rule over the 12 third-placed teams and the bracket-slotting rule, stated precisely. **Caveat note:** reference the known KO third-place conditioning issue (parked fix, `archive/docs_superpowers/2026-06-10-ko-conditioning-issue.md`; deterministic slotting prepped, awaiting the 27 June `REALIZED_THIRDS` fill) — the notes must describe current behavior and flag the caveat, without depending on the fix.
  - Knockout: Elo logistic $P(A \text{ beats } B) = \dfrac{1}{1+10^{-(R_A-R_B)/400}}$ for matchups with no market odds; the `late` rating adjustment if present in code.
  - RNG/seed and reproducibility numerics.
  - "As implemented" block + anchors.

- [ ] **Step 3: Compile check.**

- [ ] **Step 4: Commit:** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES §4: Monte Carlo tournament sampler"`

### Task 7: §5 Bracket optimization

**Files:**
- Modify: `TECHNICAL_NOTES.md` (§5)
- Read first: `scripts/predict_knockout.py` (full), `scripts/slot_value.py` (full), `scripts/pivotality.py` (full)

- [ ] **Step 1: Read all three files in full.**

- [ ] **Step 2: Write §5.** Required content:
  - How simulated advancement distributions become KO picks: `predict_knockout.py:probs` (the Elo logistic + any host adjustment — document the actual host term from the code) and `predict_pair` (the scoreline attached to a KO pick).
  - Slot value: define the quantity `slot_value.py` computes (expected points contributed by the team placed in a bracket slot) as a formula over the simulation output.
  - Pivotality: define the diagnostic `pivotality.py` computes (sensitivity of total expected points to a single pick flip) as a formula.
  - The implicit optimization: picks maximize expected pool points given the simulated distributions — state the greedy/sequential structure actually used (read the code; if it's greedy per round rather than a global argmax, say so under the honesty rule).
  - "As implemented" block + anchors.

- [ ] **Step 3: Compile check.**

- [ ] **Step 4: Commit:** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES §5: bracket optimization, slot value, pivotality"`

### Task 8: §6 ML risk check

**Files:**
- Modify: `TECHNICAL_NOTES.md` (§6)
- Read first: `scripts/ml_risk_xgb.py` (full); skim `scripts/ml_risk.py` for the non-XGB variant if referenced

- [ ] **Step 1: Read `scripts/ml_risk_xgb.py` in full.** Identify: feature vector, training target, training data, model hyperparameters, and what decision (if any) the output feeds.

- [ ] **Step 2: Write §6.** Required content:
  - The supervised problem: $y = f(x) + \varepsilon$ with the exact feature list $x$ and target $y$ from the code; gradient-boosted trees objective in one display equation (the standard XGBoost regularized objective, instantiated with the code's hyperparameters).
  - Its role: a validation/risk layer — state explicitly what it does NOT change about the locked picks (per spec: "what it does/doesn't change").
  - "As implemented" block + anchors.

- [ ] **Step 3: Compile check.**

- [ ] **Step 4: Commit:** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES §6: XGBoost risk layer"`

### Task 9: §7 Prophet measurement — match events to λ_obs

**Files:**
- Modify: `TECHNICAL_NOTES.md` (§7, opening Part II with a 2-3 sentence intro on the two-track design)
- Read first: `scripts/performance.py` (full), `scripts/calibrate_proxy.py` (full), the coefficient file loaded by `performance.py:load_coef`, `scripts/collect_match.py` (skim for what stats arrive from ESPN)

- [ ] **Step 1: Read the files; note the exact stored coefficients.**

- [ ] **Step 2: Write §7.** Required content:
  - Part II intro: Frozen Prophet (control — re-conditions on results, strengths fixed) vs Learning Prophet (strengths drift with performance); headline = the gap between tracks + which games carried information.
  - The free-data constraint: real xG is not freely available for World Cups (Understat covers top-5 leagues only) → shots-based proxy.
  - Proxy: $\hat\lambda_{obs} = \beta_1 \cdot \mathrm{SoT} + \beta_2 \cdot \mathrm{otherShots}$ with the fitted coefficients ($\beta_1 = 0.326$; read $\beta_2$ and any intercept from the coef file — document exactly what is stored).
  - Calibration: the regression `calibrate_proxy.py:fit` runs (data = 2018+2022 World Cups; document the estimator — OLS through origin or with intercept, per code) and its validation (RMSE vs the naive predictor, from `heldout_validation.py` — cite the number after reading it in Task 14, or read it here).
  - Fallback: `compute_lambda_obs(stats, real_xg=...)` uses real xG when supplied.
  - "As implemented" block + anchors.

- [ ] **Step 3: Compile check.**

- [ ] **Step 4: Commit:** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES §7: shots-based xG proxy and its calibration"`

### Task 10: §8 The expectation model — λ_exp from ratings

**Files:**
- Modify: `TECHNICAL_NOTES.md` (§8)
- Read first: `scripts/learn.py:_lambda_for_diff/lambda_expected` and whatever `_lambda_for_diff` calls in `poisson_model.py`

- [ ] **Step 1: Read the functions.** Establish exactly how a rating difference maps to expected goal rates (it routes through the Elo logistic → fair probabilities → `fit_rates`; verify and document the actual chain).

- [ ] **Step 2: Write §8.** Required content:
  - $\lambda_{exp}(d)$ where $d = R_{home} - R_{away}$: the full composition chain as one displayed pipeline of maps (Elo logistic → outcome probabilities → `fit_rates` inversion → $(\lambda_H, \lambda_A)$), each link anchored.
  - Numerics: memoization on $\mathrm{round}(d)$ (lru_cache) — note it as a pure-performance approximation with max error bounded by the λ-sensitivity to a 0.5-point rating change.
  - "As implemented" block + anchors.

- [ ] **Step 3: Compile check.**

- [ ] **Step 4: Commit:** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES §8: lambda_expected rating-to-rate map"`

### Task 11: §9 The learning update — net surprise and regularized drift

**Files:**
- Modify: `TECHNICAL_NOTES.md` (§9)
- Read first: `scripts/learn.py` (full, including `LearningTrack`)

- [ ] **Step 1: Read `learn.py` in full.** Verify the update order (decay-then-add vs add-then-decay), the clip bound, and how `LearningTrack` applies drift to both teams of a match.

- [ ] **Step 2: Write §9.** Required content:
  - Net surprise: $s = (\lambda_{obs}^{for} - \lambda_{exp}^{for}) - (\lambda_{obs}^{against} - \lambda_{exp}^{against})$ — performance relative to expectation, netted.
  - Drift update as implemented (verify exact form): $d \leftarrow \mathrm{clip}(\gamma\, d + k\, s,\ -75,\ +75)$ with locked $k = 50$, $\gamma = 0.95$, cap $\pm75$; effective rating $R_i + d_i$.
  - Interpretation paragraph: a regularized-Elo / exponential-forgetting filter; $\gamma$ = forgetting factor (information half-life $\ln 2 / \ln(1/\gamma)$ games — compute the number), $k$ = gain, cap = hard regularization; $k=0$ recovers the Frozen track exactly.
  - How $k$ was chosen: pointer to §12 (two-tournament sweep, 2022 optimum 40, 2018 optimum 60, midpoint 50).
  - "As implemented" block + anchors.

- [ ] **Step 3: Compile check.**

- [ ] **Step 4: Commit:** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES §9: net surprise and regularized drift update"`

### Task 12: §10 Re-simulation and the two-track trajectory

**Files:**
- Modify: `TECHNICAL_NOTES.md` (§10)
- Read first: `scripts/sim_tournament.py` (full), `scripts/replay.py` (full)

- [ ] **Step 1: Read both files in full.** Note `run_replay` defaults (N=4000, seed=2026, k=50) and the conditioning logic (`group_results`/`ko_results` pinned, remainder simulated).

- [ ] **Step 2: Write §10.** Required content:
  - The conditional re-simulation: after game $t$, champion distribution $p_t = P(\text{champion} \mid \text{results}_{1..t}, \text{ratings}_t)$ estimated by MC; played games pinned, future games sampled.
  - The two tracks as one equation family: Frozen uses $R_i$ fixed; Learning uses $R_i + d_{i,t}$ with $d$ from §9.
  - The generic simulator's components: `win_prob` (Elo logistic), `_sample_goals`, `group_standings`, `simulate_knockout` — each with its formula/rule and numerics ($N$, seed).
  - KO third-place conditioning caveat (same reference as §4): current limitation, parked deterministic fix, awaiting 27 June realized thirds.
  - "As implemented" block + anchors.

- [ ] **Step 3: Compile check.**

- [ ] **Step 4: Commit:** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES §10: conditional re-simulation, two-track trajectory"`

### Task 13: §11 Information accounting — KL in bits

**Files:**
- Modify: `TECHNICAL_NOTES.md` (§11)
- Read first: `scripts/snapshot.py` (full), `scripts/replay.py:champion_dist/_snapshot` (re-read)

- [ ] **Step 1: Read the files.** Confirm the KL direction ($D_{KL}(p_t \| p_{t-1})$ vs reverse), the $\varepsilon$ smoothing (1e-12), and the log base / bits conversion.

- [ ] **Step 2: Write §11.** Required content:
  - $D_{KL}(p_t \,\|\, p_{t-1}) = \sum_i p_t(i)\, \log_2 \dfrac{p_t(i)}{p_{t-1}(i)}$ bits (verify direction and base against code), with the $\varepsilon$-floor numerics.
  - Interpretation: per-game information content of the tournament — "how much did this match move the champion belief"; reference values from the 2022 replay (Japan upsets 0.13/0.09 bits vs 0.026 median).
  - Channel decomposition: result-only vs result+performance information (1.52 vs 0.26 bits, 2022 replay) — define the two channels precisely as the frozen-track KL (result channel) and the learning-minus-frozen increment (performance channel); verify the definition against how the paper/§4.9 computes it before writing (check `scripts/replay.py` and, if needed, `paper/Avraa_WC2026_paper.tex` §4.9).
  - "As implemented" block + anchors.

- [ ] **Step 3: Compile check.**

- [ ] **Step 4: Commit:** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES §11: KL information accounting"`

### Task 14: §12 How we know it works — validation math

**Files:**
- Modify: `TECHNICAL_NOTES.md` (§12)
- Read first: `scripts/heldout_validation.py` (full), `scripts/sweep_k.py` (full)

- [ ] **Step 1: Read both files in full.** Pull the actual reported numbers (CV lift +7.2 pts 2018→2022; placebo collapse +6.8 → −5.3; proxy RMSE vs naive).

- [ ] **Step 2: Write §12.** Required content:
  - Leave-one-tournament-out CV: define the evaluation metric used (read code — champion-probability points or pool points), the train/test split (tune $k$ on one WC, evaluate on the other), and the result.
  - Placebo: shuffle the xG/proxy signal across matches, re-run; the lift must vanish if learning uses real information — formula for the placebo statistic and the observed collapse.
  - k-sweep: the objective curve over $k$ for 2018 and 2022, optima 40/60, locked midpoint 50; over-reaction regime at high $k$.
  - One honest limitations paragraph: $n = 2$ tournaments, exploratory framing (consistent with the paper's reframing of §4.9).
  - "As implemented" block + anchors.

- [ ] **Step 3: Compile check.**

- [ ] **Step 4: Commit:** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES §12: held-out validation, placebo, k-sweep"`

### Task 15: Verification pass — anchor audit and constants check

**Files:**
- Modify: `TECHNICAL_NOTES.md` (fixes only)

- [ ] **Step 1: Anchor audit.** For EVERY anchor line in the document, re-open the anchored function and check the displayed equation against the code line by line. Fix discrepancies in the doc (or flag honestly if the code is the approximation).

- [ ] **Step 2: Constants check.** Extract every numeric constant from the doc (`grep -oE '[0-9]+\.?[0-9]*'` on the math lines as a starting point; manual list is fine) and grep each back to its source file. Every constant must appear in code, data, or be derived in-text. Fix any that don't.

- [ ] **Step 3: Placeholder scan.** `grep -n "pending\|TBD\|TODO" TECHNICAL_NOTES.md` — expected: no matches.

- [ ] **Step 4: Prose pass.** Re-read the full document for voice (avraa-voice), internal consistency of notation with Part 0, and section-number alignment with `HOW_THE_MODEL_WORKS.md`.

- [ ] **Step 5: Commit (if changes):** `git add TECHNICAL_NOTES.md && git commit -m "TECHNICAL_NOTES: anchor audit + constants verification fixes"`

### Task 16: PDF build, README link, ship

**Files:**
- Create: `TECHNICAL_NOTES.pdf`
- Modify: `README.md` (one line in "How it works" + repo map row)

- [ ] **Step 1: Build the PDF.**
  ```bash
  pandoc TECHNICAL_NOTES.md -o TECHNICAL_NOTES.pdf --pdf-engine=tectonic
  ```
  Expected: exit 0. Open/inspect the PDF for broken math (spot-check §3, §9, §11 — the heaviest sections).

- [ ] **Step 2: Spot-check GitHub math rendering risks.** Scan the Markdown for constructs GitHub's math renderer mishandles (`\dfrac` is fine; avoid `\begin{align}` outside `$$`; check any `*` inside math). Fix if found, rebuild PDF.

- [ ] **Step 3: Link from README.** In `README.md` under "How it works", after the `HOW_THE_MODEL_WORKS.md` line, add:
  ```markdown
  - **Technical notes (the math):** [`TECHNICAL_NOTES.md`](TECHNICAL_NOTES.md)
  ```
  and add a repo-map row for `TECHNICAL_NOTES.md` if the map lists root docs.

- [ ] **Step 4: Final commit.**
  ```bash
  git add TECHNICAL_NOTES.md TECHNICAL_NOTES.pdf README.md
  git commit -m "Ship TECHNICAL_NOTES: formula-level companion (md + pdf), linked from README"
  ```

- [ ] **Step 5: Verify clean state.** `git status` — expected: only the pre-existing KO-fix files remain modified/untracked.
