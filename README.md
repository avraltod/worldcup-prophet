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
| `archive/` | Issued paper editions, named `WC2026_paper_Gggg_Mmmm.pdf` (ggg = update order, mmm = match number; `archive/paper_versions/`) + progress reports |

## Results tracking

<!-- LIVE-RESULTS:START -->
_Last updated: 2026-06-26 — 60/104 matches played._

**Information gain in this update:** 0.042 bits

**Champion probability — model vs market (top 8):**

| Team | Model | Market |
|---|---|---|
| Spain | 26.5% | 13.7% |
| Argentina | 21.8% | 15.1% |
| France | 14.1% | 18.9% |
| Portugal | 9.0% | 8.3% |
| England | 6.5% | 10.1% |
| Brazil | 2.9% | 5.5% |
| Ecuador | 2.9% | 0.5% |
| Netherlands | 2.8% | 5.7% |

**Biggest moves:** Ecuador +2.4pp, Spain -1.5pp

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
- M13: Saudi Arabia 1–1 Uruguay
- M14: Spain 0–0 Cape Verde
- M15: Iran 2–2 New Zealand
- M16: Belgium 1–1 Egypt
- M17: France 3–1 Senegal
- M18: Iraq 1–4 Norway
- M19: Argentina 3–0 Algeria
- M20: Austria 3–1 Jordan
- M21: Ghana 1–0 Panama
- M22: England 4–2 Croatia
- M23: Portugal 1–1 Congo DR
- M24: Uzbekistan 1–3 Colombia
- M25: Czechia 1–1 South Africa
- M26: Switzerland 4–1 Bosnia and Herzegovina
- M27: Canada 6–0 Qatar
- M28: Mexico 1–0 South Korea
- M29: Brazil 3–0 Haiti
- M30: Scotland 0–1 Morocco
- M31: Turkey 0–1 Paraguay
- M32: United States 2–0 Australia
- M33: Germany 2–1 Ivory Coast
- M34: Ecuador 0–0 Curaçao
- M35: Netherlands 5–1 Sweden
- M36: Tunisia 0–4 Japan
- M37: Uruguay 2–2 Cape Verde
- M38: Spain 4–0 Saudi Arabia
- M39: Belgium 0–0 Iran
- M40: New Zealand 1–3 Egypt
- M41: Norway 3–2 Senegal
- M42: France 3–0 Iraq
- M43: Argentina 2–0 Austria
- M44: Jordan 1–2 Algeria
- M45: England 0–0 Ghana
- M46: Panama 0–1 Croatia
- M47: Portugal 5–0 Uzbekistan
- M48: Colombia 1–0 Congo DR
- M49: Scotland 0–3 Brazil
- M50: Morocco 4–2 Haiti
- M51: Switzerland 2–1 Canada
- M52: Bosnia and Herzegovina 3–1 Qatar
- M53: Czechia 0–3 Mexico
- M54: South Africa 1–0 South Korea
- M55: Curaçao 0–2 Ivory Coast
- M56: Ecuador 2–1 Germany
- M57: Japan 1–1 Sweden
- M58: Tunisia 1–3 Netherlands
- M59: Turkey 3–2 United States
- M60: Paraguay 0–0 Australia
<!-- LIVE-RESULTS:END -->
