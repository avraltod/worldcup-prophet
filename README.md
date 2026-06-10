# FIFA World Cup 2026 — A Market-Calibrated Poisson–Elo Forecast

A forecasting framework for all 104 matches of the 2026 FIFA World Cup, built for a
friends' prediction pool scored **3 points for an exact scoreline, 2 for the correct
result and goal difference, and 1 for the correct result only**. By Avralt-Od Purevjav.

## Pre-registration (the point of this repository)

**All predictions are locked before the June 11, 2026 opening match** — built four
days out from bookmaker odds, then confirmed in a final pre-kickoff review against the
closing squad and injury news. This repository is the timestamped record. Nothing in
the submitted forecast changes after the tournament starts; only the *evaluation* is added.

The central pre-registered analysis treats the pre-tournament forecast as a prior and
studies how it revises as results arrive, measuring the information each result carries
(KL divergence, in bits). Three hypotheses are registered in `experiment/protocol.md`:
information is concentrated in a few matches, spikes at eliminations of likely
champions, and arrives late (in the knockouts). These were confirmed on the 2018 and
2022 World Cups as an out-of-sample check (see the paper, §4.7).

## What's here

| Path | Contents |
|------|----------|
| `FIFA_WORLDCUP_2026_ScoreChart_Avraa.xlsx` | The submitted pool entry (locked) |
| `paper/Avraa_WC2026_paper.tex` / `.pdf` | The academic write-up |
| `experiment/protocol.md` | The pre-registered evaluation protocol + hypotheses |
| `Avraa_Prediction_WC2026.{md,html,docx}` | Shareable prediction dossier |
| `HOW_THE_MODEL_WORKS.{md,pdf}` | Plain-language explainer |
| `scripts/` | Model, simulation, conditioning, backtest, figure code |
| `data/` | Odds, Elo, predictions, trajectories; `data/backtest/` for 2018/2022 |

## Method, in one paragraph

Group-match probabilities come from margin-stripped bookmaker odds, fitted to
independent Poisson goal distributions; the predicted score is the expected-value-
optimal scoreline under the pool's rules. Knockout matchups, which the market has not
priced, use Elo win-expectancy with injury and host adjustments. A 200,000-run Monte
Carlo simulation then picks each bracket slot by *slot emergence* — the probability a
team actually reaches and wins that slot — and is validated for calibration on the
2018 and 2022 tournaments. Headline forecast: Spain champion (27%), over Argentina.

## Reproducing

Python 3.10+, with `numpy`, `scikit-learn`, `xgboost`, `matplotlib`, `openpyxl`.
Key entry points: `scripts/simulate.py` (tournament sim), `scripts/backtest.py`
(historical calibration), `scripts/record_update.py` (live updating during the
tournament). The paper compiles with `tectonic paper/Avraa_WC2026_paper.tex`.

*For a friends' pool. Not betting advice.*
