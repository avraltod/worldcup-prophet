# Pilot Report — Live Two-Track Forecaster ("Avraa's Prophet")

**Date:** 2026-06-09 (two days before the June 11 kickoff)
**Status:** PASSED — the live loop runs end to end and reacts correctly to every feed.
**Script:** `scripts/pilot.py` (reusable; edit team / news / score at the top to rehearse any scenario)

---

## 1. Objective

Confirm, before any real game is played, that the live forecasting loop works end to
end: that a **pre-kickoff news event** moves the *before* forecast, that a **result**
moves the frozen track, and that **match performance** moves the learning track — each
in the right direction — and that the information content (KL) is measured at each step.

## 2. Test design

A single fabricated scenario built to exercise all three feeds at once, on real
ratings (the 2022 structure as the working rig; the machinery is format-agnostic):

| Element | Fabricated value |
|---|---|
| Team under test | **Brazil** (pre-tournament favourite) |
| Fake news (before kickoff) | star striker injured → **−80 Elo** |
| Fake result | Brazil **0–2** Serbia (an upset loss) |
| Fake performance | Brazil out-xG's Serbia **3.0 to 0.3** (i.e. the loss was a freak) |
| Monte-Carlo | N = 5,000, seed = 2026 |

The scenario is deliberately adversarial: the *result* says Brazil collapsed, the
*performance* says Brazil dominated. A correct system must treat them differently.

## 3. Procedure and results

| Stage | Brazil champion | What it exercises |
|---|---:|---|
| **A. t = 0 baseline** | **28.5 %** | — |
| **B. + fake injury news** (−80 Elo) → *before* snapshot | **15.3 %** | the news / before-feed path (−13.2 pts; **0.075 bits** of information) |
| **C. + fake game** (0–2 loss, out-xG'd 3.0–0.3): | | the after-feed path, both tracks |
| &nbsp;&nbsp;&nbsp; → **Frozen** (conditions on the result only) | **8.9 %** | result conditioning (KL 0.049) |
| &nbsp;&nbsp;&nbsp; → **Learning** (also updates strength from xG) | **18.5 %** | performance learning (rating 2089 → 2161) |

## 4. Findings

1. **The news / before path works.** The injury moved Brazil's champion probability
   from 28.5 % to 15.3 % and registered 0.075 bits of information — exogenous news
   correctly updates the *before* forecast.
2. **The result path works.** Conditioning on the 0–2 defeat dropped the frozen track
   to 8.9 %, as it should for a favourite that loses its opener.
3. **The performance path works.** The learning track read the 3.0-vs-0.3 xG, lifted
   Brazil's strength (2089 → 2161), and held it at 18.5 % — **+9.6 points above the
   frozen track** — correctly judging the defeat to be unlucky. This is the same
   behaviour the system showed on Argentina's real 2022 loss to Saudi Arabia.
4. **The information measure works.** KL divergence was computed and non-zero at each
   transition (0.075 bits for the news, 0.049 for the game).
5. **Responsiveness observation (the useful surprise).** The learning track ended
   *higher* than the post-news snapshot (18.5 % > 15.3 %): one dominant performance
   more than offset both the injury news and the loss, and the drift reached +72 of a
   ±75 cap. The *direction* is right, but the system is very sensitive to a single
   extreme game. This is exactly what the regularisation knob `k` governs.

## 5. Verdict and recommendation

The live two-track loop is **flight-tested and ready** for June 11: news, result, and
performance each move the forecast correctly, and the frozen-vs-learning contrast
behaves as designed.

**Recommended next step before kickoff:** sweep the learning-rate knob `k` (and the
per-game drift cap) on this scenario to pick a default that is responsive without
over-reacting to one freak result — then lock it for the tournament.

## 6. Reproducibility

```
python3 scripts/pilot.py
```

Deterministic (seed = 2026). The scenario parameters (team, news delta, result,
observed xG) are constants at the top of the script and can be changed to rehearse any
event — a useful dry run on the morning of the opening match.
