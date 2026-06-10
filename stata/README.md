# Stata replication of the World Cup 2026 model

A graded, self-contained Stata port of the model's conceptual core, so you can
understand it from the inside. Each do-file is standalone and its output matches
the Python results exactly.

## How to run
Open Stata, `cd` into this folder, then `do 00_master.do` (or run the files one
at a time). Requires Stata 16+ (uses Mata). No packages needed.

## The files (a learning path)
| File | What it teaches | Verified result |
|------|-----------------|-----------------|
| `01_devig.do` | Bookmaker decimal odds carry a ~5% margin (overround). Stripping it two ways: basic normalization (what the model uses) and Shin's method. | Shin moves the home prob >1pp on 6 of 24 fixtures; the pick barely changes. |
| `02_poisson_ev.do` | **The heart.** Fit two Poisson goal rates to reproduce (P_home,P_draw,P_away), then score every scoreline by expected points under the 3/2/1 rule and pick the max. | Reproduces **all 72/72** locked picks, incl. the **2 draws**. A favorite -> 1-0; an even match -> 1-1. |
| `03_backtest.do` | Turn the Elo gap into match probabilities for 2018+2022, then score with Brier, RPS, and a calibration table. | Pooled Brier **0.599**, **10%** skill vs uniform, calibration roughly monotonic with wide bins. |

## Data (exported from the Python pipeline)
- `odds.csv` — raw decimal odds for the 24 fixtures with published lines
- `predictions.csv` — the de-vigged probabilities, fitted lambdas, and locked picks
- `backtest.csv` — 2018/2022 results with pre-tournament Elo
- `shootouts.csv` — the 24 World Cup penalty shootouts (1998-2022)

## The key formula (in 02)
For a prediction (h,a) with result r and goal difference g, expected points are
`EV(h,a) = P(exact h-a) + P(result=r AND GD=g) + P(result=r)`.
The exact score earns all three tiers, the right margin the lower two, the right
result the lowest. This single line explains every pick: favorites get a one-goal
margin, the most even games get a 1-1 draw.

## What is NOT ported
The 200,000-run 48-team tournament Monte Carlo (with the third-place bracket
allocation, slot-emergence routing, and the KL information trajectory) is an
engineering artifact better left in Python; Stata/Mata can do it but slowly. The
three files here are the conceptual core that actually teaches the model.

## Mata gotchas found while porting (for reference)
- Mata has no `factorial()`; use `exp(-lam + k*ln(lam) - lngamma(k+1))` for the Poisson pmf.
- Inside a `mata:` block, comments are `//`, not `*` (Mata reads `*` as multiply).
- This build rejects the one-line `if (c) { a; b; c }`; put the block on its own lines.
