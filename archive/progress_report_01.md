# Live Progress Report 1 — after matches 1–2

**Date:** 2026-06-12 · **Matches recorded:** 2 of 104 · **Pipeline:** automated (v2, every 20 minutes)

---

## 1. Results against the locked picks

| M | Fixture | Pick | Result | Points | E[points] | P(outcome) | Brier |
|---|---------|------|--------|--------|-----------|------------|-------|
| 1 | Mexico – South Africa | 1-0 | **2-0** | 1 | 1.02 | 0.672 | 0.166 |
| 2 | South Korea – Czechia | 1-1 | **2-1** | 0 | 0.74 | 0.361 | 0.613 |
| | **Cumulative** | | | **1** | **1.77** | | mean 0.389 |

Match 1 returned the predicted result with the wrong margin (one point of three).
Match 2 missed: the model priced the fixture as a near-coin-flip (36/30/34) and
the realistic readout settled on the draw; South Korea won it. One point against
1.77 expected is below par, on a sample of two — the running total concentrates
around its expectation only over weeks, not days.

The expected-points column uses the corrected 3/2/1 expectation
$E[S] = P(\text{result}) + P(\text{result} \wedge \text{GD}) + P(\text{exact})$. A formula error in the live
pipeline's expectation table (a stale two-tier (3,1) formula that understated
every pick by ~15 percent) was found and fixed on 2026-06-12; realized points,
outcome probabilities, and Brier scores were never affected.

## 2. What the results did to the forecast

Championship-level information content was 0.0011 bits (M1) and 0.0008 bits
(M2) — both essentially zero, consistent with the pre-registered hypothesis
that early group results barely move the title race. The champion table:
Spain 27.1% → 26.9%, Argentina 18.1% → 18.3%, France 14.3% → 14.4% — all
within Monte-Carlo noise of flat.

Inside Group A, however, the two results moved a great deal:

| Team | Pts | GD | Advance (frozen → now) | Reach R16 | Reach QF |
|------|-----|----|------------------------|-----------|----------|
| Mexico | 3 | +2 | 91.8% → **98.7%** | 58.5% → 62.8% | 27.0% → 29.2% |
| South Korea | 3 | +1 | 66.2% → **92.5%** | 27.8% → 41.3% | 8.1% → 12.5% |
| Czechia | 0 | −1 | 68.0% → **50.5%** | 27.0% → 18.4% | 7.1% → 4.9% |
| South Africa | 0 | −2 | 45.6% → **32.5%** | 8.1% → 5.3% | 0.9% → 0.5% |

The locked forecast had Czechia and South Korea effectively tied for the
runner-up spot (68.0 vs 66.2) and named their opener as the decider; the
opener has now decided it. Korea's single win was worth +26 points of
qualification probability, because beating the direct rival is a double swing.
Reality is converging on the locked finishing order — Mexico first, Korea
second, Czechia advancing as a third-placer.

Spillover outside Group A is real but an order of magnitude smaller (largest
moves ±1.5 points, via the M73 routing, the third-place pool, and the T-slot
draw). No champion probability moved beyond noise.

## 3. Machinery

The full automated cycle has now run end to end on real matches:
PRE M1 (17:58Z, 62 min before kickoff) → POST M1 (21:10Z) → PRE M2 (01:31Z,
28 min before kickoff, conditioned on M1) → POST M2 (04:14Z). One incident:
GitHub's cron scheduler went silent for three slots (02:42–04:15Z); the
hold-on-doubt gate ensured nothing was lost and the POST published on the
next firing. No action needed, but the pattern is worth watching — if skips
recur, moving the schedule off the congested :05/:25/:45 marks is the cheap
hardening.

## 4. Next up

| M | Fixture | Pick | E[points] |
|---|---------|------|-----------|
| 3 | Canada – Bosnia and Herzegovina | 2-1 | 0.87 |
| 4 | United States – Paraguay | 2-1 | 0.88 |
| 8 | Qatar – Switzerland | 1-2 | 1.06 |

Group A is idle until matchday 2 (M25 Czechia – South Africa, June 19 —
now near-must-win for Czechia; M28 Mexico – South Korea, the de facto
group-winner decider).

---

*Generated from the live v2 records (`data/trajectory_v2.json`), the corrected
expectation table (`data/match_expectations.json`), and conditioned
re-simulation at N=30,000. Part of the pre-registered worldcup-prophet
project; the locked forecast is unchanged at tag `prereg-2026`.*
