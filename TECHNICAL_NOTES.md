# Technical Notes: The Model in Formulas
### The companion in formulas — every pipeline step as the mathematics it implements. Reads side-by-side with [HOW_THE_MODEL_WORKS.md](HOW_THE_MODEL_WORKS.md).

---

## Part 0. Notation and contract

Throughout, $i$ indexes teams and $R_i$ is team $i$'s Elo rating (a scalar strength,
e.g. Spain 2165, Qatar 1423). A match between a designated home side $H$ and away side
$A$ produces a scoreline $(h,a) \in \mathbb{Z}_{\ge 0}^2$. The model's prediction for a
match is a scoreline $(\hat h, \hat a)$. Goal rates are $\lambda_H, \lambda_A > 0$:
the expected goals of each side under a Poisson model. Outcome probabilities are the
triple $(p_H, p_D, p_A)$ — home win, draw, away win — and $o_j$ denotes a decimal
bookmaker odds quote for outcome $j \in \{H, D, A\}$. The pool's score function is
$S(\hat h, \hat a;\, h, a) \in \{0, 1, 2, 3\}$ (defined in §0). In Part II, $p_t$
denotes the champion probability distribution over all 48 teams after conditioning on
the first $t$ played games, and $d_i$ is team $i$'s learned rating drift.

Two contracts hold for the whole document:

1. **Anchor contract.** Every displayed equation is followed by an anchor naming the
   code that implements it — `scripts/file.py:function` — with the constants as locked
   before kickoff (2026-06-10). The formulas are extracted from the code, not from an
   idealized model.
2. **Honesty rule.** Where the code is a pragmatic shortcut rather than clean
   statistics (an independence assumption, a proportional vig split, a memoized grid),
   the note says so explicitly rather than dressing it up.

---

# Part I — The locked forecast

*(Sections 0–6 mirror stages 0–6 of HOW_THE_MODEL_WORKS.md, same numbers.)*

## 0. The goal shapes everything — the 3/2/1 objective as a decision problem

The pool awards points per match by comparing the predicted scoreline
$(\hat h, \hat a)$ to the realized one $(h, a)$. Write the realized result as
$r = \operatorname{sgn}(h - a) \in \{+1, 0, -1\}$ (home win, draw, away win) and the
predicted result as $\hat r = \operatorname{sgn}(\hat h - \hat a)$. The score function
is

$$
S(\hat h, \hat a;\, h, a) =
\begin{cases}
3 & \text{if } (\hat h, \hat a) = (h, a) \\
2 & \text{if } \hat r = r \text{ and } \hat h - \hat a = h - a \\
1 & \text{if } \hat r = r \\
0 & \text{otherwise.}
\end{cases}
$$

*Anchor: `scripts/scoring.py:score_match` — tiers checked in exactly this order
(exact, then result+goal-difference, then result).*

The tiers are **nested**: an exact hit implies the right goal difference, which
implies the right result. So the score decomposes into three indicator variables,

$$
S = \mathbf{1}[\hat r = r] \;+\; \mathbf{1}[\hat r = r,\ \hat h - \hat a = h - a]
\;+\; \mathbf{1}[(\hat h, \hat a) = (h, a)],
$$

and taking expectations under the match's scoreline distribution $P(h, a)$ gives the
identity the code actually computes:

$$
\mathbb{E}\,[S(\hat h, \hat a)] \;=\; P(\text{result}) \;+\;
P(\text{result and goal difference}) \;+\; P(\text{exact}).
$$

*Anchor: `scripts/ev321.py:ev_321` — returns `p_exact + p_rg + p_r`, the three terms
summed over the scoreline grid $\{0,\dots,8\}^2$ (`MAX_G = 8`).*

**The decision problem.** Given a scoreline distribution $P(h,a)$ for the match
(built in §3), the model's pick is the expected-points maximizer

$$
(\hat h, \hat a) \;=\; \underset{(\hat h, \hat a)\, \in\, \{0,\dots,8\}^2}{\arg\max}\;
\mathbb{E}\,[S(\hat h, \hat a;\, h, a)],
$$

found by brute force over all $81$ candidate scorelines.

*Anchor: `scripts/ev321.py:best_pick` — exhaustive search over the $9 \times 9$ grid;
ties keep the first maximizer encountered in row-major order.*

**Why this is not "pick the most likely result."** The objective rewards margins, not
just winners, and that changes the optimum in two systematic ways:

1. *One-goal margins dominate.* For realistic goal rates, the goal-difference tier
   $P(h - a = 1)$ concentrates on $\hat h - \hat a = 1$, pulling picks toward 1-0
   and 2-1 (made precise in §3).
2. *Draws pool their goal difference.* Every draw shares $h - a = 0$, so a 1-1
   prediction banks the 2-point tier on **any** drawn scoreline:

$$
\mathbb{E}\,[S(1,1)] \;=\; 2\,p_D \;+\; P(1,1) ,
$$

since $\mathbf{1}[\hat r = r]$ and the goal-difference indicator coincide whenever the
match is drawn. No win prediction enjoys this pooling — a 1-0 pick needs the margin
to be exactly one. On evenly-matched games ($p_D$ near its Poisson ceiling), 1-1 is
therefore the expected-points optimum even when neither side is a likely winner.

**As implemented.** `ev321.py` evaluates $\mathbb{E}[S]$ exactly (no simulation) on
the truncated grid $\{0,\dots,8\}^2$; the truncation error is the Poisson tail mass
beyond 8 goals, negligible at football rates ($P(X > 8) < 10^{-5}$ at
$\lambda = 2$). `scoring.py:score_match` applies the same tiers to realized results
during the live run, alongside two diagnostics: the outcome probability assigned to
the realized result, and the Brier score
$\sum_{j \in \{H,D,A\}} (p_j - \mathbf{1}[j = r])^2$.

## 1. Inputs — from information to numbers

Everything downstream is arithmetic on numbers, so the first real modeling step is
**measurement**: turning four kinds of worldly information into typed numerical
objects. This section gives the encoding map for each.

**(a) Bookmaker odds $\to$ probability triples.** Each group fixture is one JSON
record carrying decimal odds and their implied fair probabilities:

$$
\text{quote } (o_H, o_D, o_A) \;\longmapsto\; (p_H, p_D, p_A), \qquad
p_j \propto 1/o_j
$$

(the normalization is §2's subject). Odds were hand-collected June 2–7, 2026 from
bet365, FanDuel, DraftKings, Betfair, oddschecker/oddspedia aggregators, and
sportytrader composites including Kalshi/Polymarket — one source per fixture, recorded
in a `source` field (e.g. `"FanDuel 2026-06-05"`), not averaged across books. The
loader merges three files (`odds_AD.json`, `odds_EH.json`, `odds_IL.json`, 24
fixtures each = 72), keys them by the canonicalized team pair, flips home/away
orientation if a quote was stored reversed, and **defensively renormalizes**
$p_j \leftarrow p_j / (p_H + p_D + p_A)$ so rounding in the stored triples cannot
leak through.

*Anchor: `scripts/predict_groups.py:load_odds` + `main` — pair-keyed merge,
orientation flip, renormalization.*

For matchday-3 fixtures with no published odds at collection time, the probability
triple is instead an **Elo estimate** (the §3 logistic applied to the two ratings,
flagged in `source`, e.g. `"Elo estimate (ARG 2113, AUT 1830)"`) — the weakest data
tier, used for roughly a third of the group slate.

**(b) Elo table $\to$ ratings $R_i$.** One integer per team for all 48 teams
(Spain 2165 down to Qatar 1423), read from `data/elo_outright_news.json` as collected
June 5–7, 2026. The effective knockout rating adds two deterministic corrections:

$$
R_i^{\mathrm{eff}} \;=\; R_i \;+\; \delta_i^{\mathrm{inj}} \;+\;
\delta_i^{\mathrm{host}},
$$

with the injury and host terms defined in (c) and §4.

*Anchor: `scripts/simulate.py:ko_rating` — `ELO[team] + ADJ.get(team, 0)` plus the
host bonus.*

**(c) Team news $\to$ additive rating penalties.** Qualitative injury reports are
encoded as fixed Elo deductions $\delta_i^{\mathrm{inj}}$, set once at collection
time:

| Team | $\delta^{\mathrm{inj}}$ | Reason on record |
|---|---|---|
| Netherlands | $-23$ | Xavi Simons out |
| Brazil | $-20$ | Rodrygo out |
| Japan | $-10$ | Mitoma out |
| Croatia | $-10$ | squad fitness |
| Spain | $-5$ | Fermín López out (metatarsal) |

This is the bluntest measurement in the pipeline — a hand-set scalar per absence,
not a player-value model — and is flagged as such per the honesty rule.

*Anchor: `data/elo_outright_news.json:injury_elo_adj`, applied in
`scripts/simulate.py:ko_rating`.*

**(d) Tournament structure $\to$ fixture list + bracket graph.** The 72 group
fixtures are a static table `(row, group, home, away)`; the knockout is a directed
graph encoded as the sheet's slot layout (16 R32 pairs feeding 8 R16 pairs, 4 QF, 2
SF, final + third-place playoff). Two auxiliary encodings matter:

- **Name canonicalization**: a deterministic alias map (`"Türkiye"` $\to$
  `"Turkey"`, `"Korea Republic"` $\to$ `"South Korea"`, …) so that every data source
  keys to one team identity — the unglamorous half of information-to-data.
- **Match numbering**: a fixed bijection between sheet rows 4–75 and FIFA's official
  group-match numbers 1–72, cross-checked by a unit test, so results logged by match
  number join correctly to predictions made by row.

*Anchor: `scripts/fixtures.py:GROUP_FIXTURES/KNOCKOUT/ALIASES/canon/ROW_MATCH`
(numbering guarded by `tests/test_match_numbering.py`).*

**As implemented.** All four inputs are frozen files under `data/` committed before
kickoff (locked 2026-06-10, tag `prereg-2026`); nothing in Part I re-reads the
outside world. The model's information set is exactly: one odds quote per fixture,
one Elo integer per team, five injury scalars, and the bracket wiring.

## 2. Clean the odds — de-vigging

A decimal quote $o_j$ implies probability $1/o_j$, but a book's implied probabilities
sum to more than one. The excess is the **overround** (vig),

$$
V \;=\; \sum_{j \in \{H, D, A\}} \frac{1}{o_j} \;-\; 1 \;>\; 0,
$$

the bookmaker's built-in margin. The model strips it by **proportional
normalization**:

$$
p_j \;=\; \frac{1/o_j}{\sum_{k \in \{H, D, A\}} 1/o_k},
\qquad j \in \{H, D, A\}.
$$

**Worked example** (the one in the companion's §2): implied $0.50/0.30/0.28$ sums to
$1.08$, so $V = 8\%$; dividing through gives fair probabilities
$0.463/0.278/0.259$ — the "46/28/26" of the plain-language walkthrough. A real one
from the data: Mexico–South Africa at $(1.40, 4.60, 8.00)$ implies
$(0.714, 0.217, 0.125)$, $V = 5.6\%$, normalizing to the stored
$(0.676, 0.206, 0.118)$.

**What proportional de-vigging assumes — honesty note.** Dividing by the total
spreads the vig across outcomes *in proportion to their implied probability*. That is
the standard first-order method, but it is a modeling choice: books are known to
shade longshots more than favorites (the favorite–longshot bias), which power or
Shin-type de-vigging methods would correct by shrinking small $1/o_j$ relatively
more. The pipeline knowingly uses the proportional map — the bias is second-order at
World Cup group-match prices, and the downstream pick rule (§3) is insensitive to
probability perturbations of that size.

**As implemented.** De-vigging is applied at data-entry time — each odds record
stores both the raw quotes $(o_H, o_D, o_A)$ and the normalized triple
$(p_H, p_D, p_A)$, so the transformation is auditable per fixture — and the loader
re-applies the same normalization defensively against rounding drift in the stored
values.

*Anchor: `data/odds_*.json` (fields `odds_*` and `p_*`);
`scripts/predict_groups.py:main` — `ph, pd, pa = ph/s, pd/s, pa/s`.*

## 3. Predict each match — the Poisson scoreline model

**The model.** Goals are independent Poisson counts:

$$
P(h, a) \;=\; \mathrm{Pois}(h; \lambda_H)\,\mathrm{Pois}(a; \lambda_A)
\;=\; e^{-\lambda_H} \frac{\lambda_H^{h}}{h!} \cdot
e^{-\lambda_A} \frac{\lambda_A^{a}}{a!},
$$

truncated to the grid $(h, a) \in \{0, \dots, 8\}^2$ everywhere.

*Anchor: `scripts/poisson_model.py:pois` (`MAX_G = 8`).*

*Honesty note:* real scorelines exhibit mild dependence between the two counts
(bivariate-Poisson and Dixon–Coles corrections exist for exactly this); the pipeline
uses independence throughout. At World Cup rates the correction mostly reweights
low-scoring draws, and the pick rule below conditions on the predicted outcome
anyway, which absorbs most of the effect.

**The inverse problem.** The market gives $(p_H, p_D, p_A)$; the model needs rates.
Outcome probabilities under the model are the grid sums

$$
\tilde p_H(\lambda_H, \lambda_A) = \sum_{h > a} P(h, a), \quad
\tilde p_D = \sum_{h = a} P(h, a), \quad
\tilde p_A = \sum_{h < a} P(h, a),
$$

and `fit_rates` inverts the map by constrained least squares on a lattice:

$$
(\hat\lambda_H, \hat\lambda_A) \;=\;
\underset{\substack{\lambda_H,\, \lambda_A \,\in\, \{0.10,\, 0.15,\, \dots,\, 3.50\} \\
1.6 \,\le\, \lambda_H + \lambda_A \,\le\, 3.4}}{\arg\min}
\;\sum_{j \in \{H, D, A\}} \bigl(\tilde p_j(\lambda_H, \lambda_A) - p_j\bigr)^2 .
$$

The lattice step is $0.05$; the total-goals band $[1.6, 3.4]$ encodes the prior that
World Cup group games average roughly $2.5$–$2.7$ total goals while letting lopsided
matches drift higher. Three targets, two parameters: the system is overdetermined and
the fit is a projection, not an interpolation.

*Anchor: `scripts/poisson_model.py:outcome_probs/fit_rates` —
`steps = 0.05k, k = 2..70`; `outcome_probs` is `lru_cache`d so the
$69 \times 69$ grid search costs one pass.*

**Worked example** (Netherlands–Japan, the companion's §3): fair probabilities
$(0.46, 0.26, 0.28)$ fit to $(\hat\lambda_{\mathrm{NED}}, \hat\lambda_{\mathrm{JPN}})
= (1.5, 1.1)$, under which $P(1,1) = 12.3\%$ is the modal scoreline but the modal
*outcome* is a Netherlands win.

**Three pick rules, one published readout.** The pipeline distinguishes:

1. **EV-optimal** (§0): $\arg\max\, \mathbb{E}[S]$ over all 81 scorelines — the
   theoretical optimum under the pool rule.
2. **Modal-conditional**: most likely scoreline *conditional on the modal outcome*,

$$
(\hat h, \hat a) \;=\; \underset{(h, a)\,:\ \mathrm{sgn}(h - a)\, =\, r^*}{\arg\max}\; P(h, a),
\qquad r^* = \underset{j \in \{H,D,A\}}{\arg\max}\; p_j ,
$$

   which never predicts a draw for a match it calls a win. Checked exhaustively:
   it matches rule 1 on **71 of 72** group fixtures.
   *Anchor: `scripts/poisson_model.py:modal_score`.*
3. **Realistic readout** (the published picks, revised pre-kickoff 2026-06-10):
   round the fitted expected goals while preserving the locked result $r^*$,

$$
(\hat h, \hat a) =
\begin{cases}
(k, k),\ \ k = \mathrm{round}\!\bigl(\tfrac{\lambda_H + \lambda_A}{2}\bigr)
  & r^* = D \\[4pt]
\bigl(\mathrm{round}(\lambda_H),\, \mathrm{round}(\lambda_A)\bigr)
\ \text{reordered, winner bumped } {+1} \text{ if level}
  & r^* \in \{H, A\}.
\end{cases}
$$

   In knockouts the locked winner takes the higher score; if the rounded scores tie
   and the winner's rate edge is below $0.25$ goals, the pick is a level score
   decided on penalties.
   *Anchor: `scripts/realistic_scores.py:realistic/ko_realistic` — pen threshold
   `(lw - ll) >= 0.25`.*

The revision is evidence-based, not aesthetic: on the 128 real matches of 2018+2022,
the realistic readout lands 18/128 exact scores versus 16 for the EV pick and is
about 10% closer in total-goals error, at no measurable pool-points cost
(`scripts/backtest.py`). The *model* — probabilities, bracket, champion — is
unchanged; only the scoreline readout differs.

**Why the optimum lives at 1-0 / 2-1 / 1-1.** Under rule 1 the margin tier makes
$P(h - a = \hat h - \hat a,\ \hat r = r)$ the dominant term. For a favorite at
World Cup rates, $P(h - a = 1) > P(h - a = m)$ for any $m \ge 2$ (Skellam mass
concentrates at small margins), so the optimal winning pick carries margin one, and
among margin-one scores the lowest-scoring (1-0) has the largest exact-hit
probability since $P(h,a)$ decays in $h + a$. For near-even matches, §0's pooling
identity $\mathbb{E}[S(1,1)] = 2 p_D + P(1,1)$ beats every win pick whose
$p_{r^*} \approx p_D$. Netherlands–Japan resolves accordingly: NED favored, so the
pick is the modal Netherlands-win score 1-0, not the modal score 1-1.

**Knockout probabilities without a market.** Undrawn knockout ties have no odds, so
$(p_H, p_D, p_A)$ is synthesized from effective Elo ratings
($d = R_H^{\mathrm{eff}} - R_A^{\mathrm{eff}}$, §1b):

$$
e = \frac{1}{1 + 10^{-d/400}}, \qquad
p_D = 0.30\, e^{-|d|/700}, \qquad
p_H = \max\!\bigl(0.01,\ e - \tfrac{p_D}{2}\bigr), \qquad
p_A = \max(0.01,\ 1 - p_H - p_D),
$$

renormalized to sum to one, then fed through the same `fit_rates` inversion. The
draw share $0.30\,e^{-|d|/700}$ is a calibration choice: 30% for dead-even ties,
decaying as the mismatch grows. A 100-point Elo gap gives $e \approx 0.64$; 200
points $\approx 0.76$.

*Anchor: `scripts/realistic_scores.py:main` (KO branch); the same logistic appears
in `scripts/predict_knockout.py:probs` (§5).*

**As implemented.** Group rates come from market triples (§2); KO rates from the
Elo synthesis above; both pass through the same lattice inversion. All probability
arithmetic is exact on the truncated grid — no simulation enters until §4.

## 4. Simulate the tournament 200,000 times — the Monte Carlo sampler

**The estimand.** Quantities like "P(Spain champion)" have no closed form — the
bracket chains 104 dependent matches through standings, third-place allocation, and
knockout routing. They are expectations over tournament realizations $\omega$,

$$
\theta \;=\; \mathbb{E}\,[\,\mathbf{1}\{\text{event}(\omega)\}\,]
\;\approx\; \hat\theta_N \;=\; \frac{1}{N} \sum_{n=1}^{N}
\mathbf{1}\{\text{event}(\omega_n)\},
$$

estimated by drawing $N$ full tournaments. The locked run used $N = 200{,}000$, so
the Monte Carlo standard error at a champion-scale probability is

$$
\mathrm{SE}(\hat\theta) \;=\; \sqrt{\frac{\theta(1 - \theta)}{N}}
\;\approx\; \sqrt{\frac{0.27 \times 0.73}{200{,}000}} \;\approx\; 0.001,
$$

i.e. about $\pm 0.1$ percentage points — the "stable, not simulation noise" claim of
the companion, made exact.

*Anchor: `scripts/simulate.py` — `N_SIMS = int(sys.argv[1])` (default 20,000; the
published run passed 200,000), `random.seed(2026)`.*

**One tournament draw.** Each $\omega_n$ is generated in four stages:

*(i) Group scorelines.* Every group match draws an exact score from its fitted rates
(§3) by inverse-CDF sampling of each truncated Poisson independently:

$$
h \sim \mathrm{Pois}(\lambda_H) \wedge 8, \qquad
a \sim \mathrm{Pois}(\lambda_A) \wedge 8,
$$

where the residual tail mass beyond 8 collapses onto 8.

*Anchor: `scripts/simulate.py:sample_score` — cumulative-sum inversion of
`pois(k, lam)` over $k = 0..8$.*

*(ii) Standings.* Group tables sort descending by the key

$$
\bigl(\text{Pts},\ \text{GD},\ \text{GF},\ U\bigr), \qquad U \sim \mathrm{Unif}(0,1),
$$

with one correction: if two adjacent teams tie exactly on all three stats, their
head-to-head result (if decisive) reorders them. *Honesty note:* FIFA's full
tiebreaker cascade includes multi-team head-to-head mini-tables, fair-play points,
and drawing of lots; the code implements Pts/GD/GF + pairwise head-to-head + a
random tail. The cheap approximation matters only on exact three-stat ties, which
carry little probability mass.

*Anchor: `scripts/simulate.py:simulate_group` — sort key
`(pts, gd, gf, random.random())`, two-way h2h swap.*

*(iii) Third-place qualification and slotting.* The 12 third-placed teams rank by
the same $(\text{Pts}, \text{GD}, \text{GF}, U)$ key; the top 8 advance. FIFA's
allocation table is encoded as a constraint set per R32 slot — e.g. match 74 may
only receive a third from groups $\{A,B,C,D,F\}$ — and the 8 qualifiers are placed
by **bipartite matching**, solved by backtracking with the candidate order shuffled
so that, when several feasible assignments exist, the simulation samples among them
rather than fixing one. If the drawn combination of groups admits no feasible
matching, the 8th-ranked third is swapped for the 9th; a still-infeasible draw is
discarded.

*Anchor: `scripts/simulate.py:THIRD_SLOTS/assign_thirds` and the qualification block
in the main loop.*

*Caveat (known issue, documented 2026-06-10):* sampling among feasible third-place
assignments is fine for the **pre-tournament** forecast — champion and advancement
probabilities are measurably identical under random vs deterministic slotting,
because advancement depends on ranking top-8-among-thirds, not on which slot a team
fills. It becomes a problem when **conditioning on realized knockout results**
(§10): a recorded R32 winner who is a third-placed team is honored only in the
iterations that happened to slot that team into that match. A deterministic fix is
prepped in `scripts/condition.py`, pending FIFA's announced bracket (~27 June); see
`archive/docs_superpowers/2026-06-10-ko-conditioning-issue.md`.

*(iv) Knockouts.* Each tie is a single Bernoulli draw from the Elo logistic on
effective ratings (§1b):

$$
P(A \text{ beats } B) \;=\; \frac{1}{1 + 10^{-(R_A^{\mathrm{eff}} -
R_B^{\mathrm{eff}})/400}} .
$$

There is no separate draw state: the logistic is read as the probability of
advancing *by any means*, extra time and shootout included ("Elo-weighted
shootout"). The host bonus decays in the late rounds: $+40$ through R32/R16, $+20$
from the quarter-finals on (crowds matter less in one-off late games at neutral-ish
venues).

*Anchor: `scripts/simulate.py:ko_rating/ko_winner` — `late=True` for QF/SF/final;
bracket wiring in dicts `R32/R16/QF/SF`.*

**Outputs.** Counters over the $N$ draws give champion / finalist / semi-finalist
distributions, per-matchup materialization rates for the sheet's predicted bracket
("how often does Germany–France actually happen at match 89"), and the per-slot
winner distribution that §5 turns into picks. A second pass with the RNG reseeded to
2026 recomputes the slot-winner counters so both passes see identical group-stage
randomness.

**As implemented.** Plain `random` (Mersenne Twister), single seed 2026, no variance
reduction — at $N = 200{,}000$ none is needed. The fitted rates are computed once
per fixture before the loop (the `lru_cache` on `outcome_probs` makes the lattice
inversion a one-time cost), so a draw is $72$ score samples plus $\le 32$ Bernoulli
draws.

## 5. Optimize the bracket — slot emergence as a formula

*(section pending)*

## 6. Check the risk — the machine learning layer

*(section pending)*

---

# Part II — Avraa's Prophet: the self-learning forecaster

## 7. Measurement: from match events to $\lambda_{obs}$

*(section pending)*

## 8. The expectation model: $\lambda_{exp}$ from ratings

*(section pending)*

## 9. The learning update: net surprise and regularized drift

*(section pending)*

## 10. Re-simulation and the two-track trajectory

*(section pending)*

## 11. Information accounting: KL divergence in bits

*(section pending)*

## 12. How we know it works: held-out validation, placebo, k-sweep

*(section pending)*
