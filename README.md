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

- **The picks:** [`PREDICTION_WC2026.md`](PREDICTION_WC2026.md) — full match-by-match
  and tournament predictions.
- **Champion call:** Spain.

## How it works

- **Method writeup:** [`HOW_THE_MODEL_WORKS.md`](HOW_THE_MODEL_WORKS.md)
- **Full paper:** [`paper/WC2026_paper.pdf`](paper/WC2026_paper.pdf)

The forecast starts from public bookmaker odds (converted to fair probabilities), applies a
Poisson goal model, and optimizes picks under the pool's 3/2/1 scoring rule.

## Verify it yourself

- Input + prediction data: [`data/`](data/)
- Model & pipeline code: [`scripts/`](scripts/)
- Tests: `pytest`

## Repository map

| Path | Contents |
|------|----------|
| `PREDICTION_WC2026.md` | The locked predictions |
| `HOW_THE_MODEL_WORKS.md` | Plain-language method |
| `paper/` | The formal paper (`WC2026_paper.pdf` + LaTeX source + figures) |
| `data/` | Locked input odds and generated predictions |
| `scripts/` | Operational pipeline, paper build, and live-update code |
| `stata/` | Stata replication scripts and backing data |
| `tests/` | Test suite |
| `experiment/ledger.csv` | Match-by-match scoring ledger |
| `archive/` | Issued paper editions M000, M001, … (`archive/paper_versions/`) + progress reports |

## Results tracking

<!-- LIVE-RESULTS:START -->
_Last updated: 2026-06-15 — 12/104 matches played._

**Information gain in this update:** 0.003 bits

**Champion probability — model vs market (top 8):**

| Team | Model | Market |
|---|---|---|
| Spain | 26.6% | 16.0% |
| Argentina | 18.2% | 7.9% |
| France | 14.7% | 16.1% |
| Portugal | 9.5% | 10.6% |
| England | 7.1% | 9.5% |
| Brazil | 3.7% | 6.6% |
| Germany | 2.2% | 6.1% |
| Netherlands | 2.2% | 5.1% |

**Biggest moves:** Spain -0.5pp

**Recorded group results:**

- M1: Mexico 2–0 South Africa
- M2: South Korea 2–1 Czechia
- M3: Canada 1–1 Bosnia and Herzegovina
- M4: United States 4–1 Paraguay
- M5: Haiti 0–1 Scotland
- M6: Australia 2–0 Turkey
- M7: Brazil 1–1 Morocco
- M8: Qatar 1–1 Switzerland
- M9: Ivory Coast 1–0 Ecuador
- M10: Germany 7–1 Curaçao
- M11: Netherlands 2–2 Japan
- M12: Sweden 5–1 Tunisia
<!-- LIVE-RESULTS:END -->
