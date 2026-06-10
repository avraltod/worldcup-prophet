# Structured Content — How Avraa's Prediction Model Works

**Title:** HOW THE MODEL WORKS — Avraa's FIFA 2026 Prediction Engine
**Subtitle:** From raw data to a filled bracket, in five stages
**Learning objective:** Understand what goes in, how it's analyzed, and what comes out.

## STAGE 1 — INPUTS (what goes in)
Four data sources, collected June 5–7, 2026:
- 💰 **Bookmaker odds** — bet365, Polymarket, Kalshi → match win/draw/loss probabilities
- 📊 **Elo ratings** — strength score for all 48 teams (e.g. Spain 2165, Qatar 1423)
- 🏥 **Team news** — confirmed injuries (Rodrygo out, Xavi Simons out, Mitoma out)
- 🗺️ **Tournament structure** — fixtures, venues, the 48-team bracket & 3rd-place rules

## STAGE 2 — CLEAN THE ODDS
- Strip the bookmaker's profit margin → **fair probabilities** that sum to 100%
- Where no odds exist (matchday 3), fall back to Elo-based estimates

## STAGE 3 — PREDICT EACH MATCH
- 🎯 **Poisson goal model:** turn each match's probabilities into the **most likely exact score** (group stage) — that's why most picks are 1-0 or 2-0
- ⚔️ **Elo win-expectancy:** decide hypothetical knockout matchups the market hasn't priced

## STAGE 4 — SIMULATE THE TOURNAMENT 200,000×
- 🎲 Play the whole World Cup **200,000 times**, letting luck and upsets happen
- 🧩 **Slot-emergence:** pick the team most likely to actually *reach AND win* each bracket slot — not just the stronger team
- This is why Portugal advances deep and England knocks out Brazil

## STAGE 5 — CHECK THE RISK (machine learning)
- 🌲 **Random Forest + XGBoost** find which results matter most to the bracket
- Finding: getting **Spain out of Group H** right is the single highest-leverage call
- Honest result: group stage explains only **~50%** of the score — the rest is luck

## OUTPUT (what comes out)
- ✅ **104 match predictions** (the submitted score sheet)
- 🏆 **Champion: Spain 27%**, beats Argentina in the final
- 📈 Full bracket + every team's survival odds + a ranked risk list

## Flow
INPUTS → CLEAN → PREDICT MATCHES → SIMULATE 200k → ML RISK CHECK → FILLED BRACKET

## Design notes
- Left-to-right (or top-to-bottom) pipeline with arrows between stages.
- Each stage is a labeled box/node with its icon. Numbers exact, no invented stats.
- Scientific but friendly — this explains the engine to non-experts.
- By Avralt-Od Purevjav · June 7, 2026
