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

*(section pending)*

## 2. Clean the odds — de-vigging

*(section pending)*

## 3. Predict each match — the Poisson scoreline model

*(section pending)*

## 4. Simulate the tournament 200,000 times — the Monte Carlo sampler

*(section pending)*

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
