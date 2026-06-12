# worldcup-prophet — Pre-Registered World Cup 2026 Forecast

**A timestamped, public, pre-registered forecast of the 2026 FIFA World Cup.**
Every prediction in this repository was committed publicly on **2026-06-10**, before the
first match (**2026-06-11**). The forecast has not been altered since the lock.

## The lock (proof)

- Locked commit: [`3ebbb8f`](../../commit/3ebbb8f) — *"Pre-registered FIFA 2026 forecast:
  predictions locked before kickoff."*
- Immutable tag: [`prereg-2026`](../../releases/tag/prereg-2026) points at that commit.
  Check it out to see the exact locked state and its date:
  ```bash
  git checkout prereg-2026
  ```

## What's predicted

- **The picks:** [`Avraa_Prediction_WC2026.md`](Avraa_Prediction_WC2026.md) — full match-by-match
  and tournament predictions.
- **Champion call:** Spain.

## How it works

- **Method writeup:** [`HOW_THE_MODEL_WORKS.md`](HOW_THE_MODEL_WORKS.md)
- **Technical notes (the math):** [`TECHNICAL_NOTES.md`](TECHNICAL_NOTES.md)
- **Full paper:** [`paper/Avraa_WC2026_paper.pdf`](paper/Avraa_WC2026_paper.pdf)

The forecast starts from public bookmaker odds (converted to fair probabilities), applies a
Poisson goal model, and optimizes picks under the pool's 3/2/1 scoring rule.

## Verify it yourself

- Input + prediction data: [`data/`](data/)
- Model code: [`scripts/`](scripts/)
- Tests: `pytest`

## Repository map

| Path | Contents |
|------|----------|
| `Avraa_Prediction_WC2026.md` | The locked predictions |
| `HOW_THE_MODEL_WORKS.md` | Plain-language method |
| `TECHNICAL_NOTES.md` | The same pipeline in formulas, anchored to the code |
| `paper/` | The formal paper (`Avraa_WC2026_paper.pdf` + LaTeX source + figures) |
| `data/` | Locked input odds and generated predictions |
| `scripts/` | Model, simulation, and analysis code |
| `tests/` | Test suite |
| `archive/` | Supporting material — drafts, alternate formats, dev notes. **Not part of the locked forecast.** |

## Results tracking

<!-- LIVE-RESULTS:START -->
_Last updated: 2026-06-12 — 2/104 matches played._

**Information gain in this update:** 0.002 bits

**Champion probability — model vs market (top 8):**

| Team | Model | Market |
|---|---|---|
| Spain | 26.9% | 16.4% |
| Argentina | 17.9% | 8.5% |
| France | 14.3% | 15.5% |
| Portugal | 9.3% | 10.5% |
| England | 7.1% | 10.1% |
| Brazil | 3.6% | 8.2% |
| Netherlands | 2.3% | 4.2% |
| Germany | 2.2% | 5.0% |

**Recorded group results:**

- M1: Mexico 2–0 South Africa
- M2: South Korea 2–1 Czechia
<!-- LIVE-RESULTS:END -->
