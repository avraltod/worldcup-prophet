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

*(section pending)*

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
