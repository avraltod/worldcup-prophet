# How Avraa's World Cup 2026 Prediction Model Works
### A detailed, plain-language walkthrough — from raw data to a filled bracket

---

## 0. The goal shapes everything

Before any math, understand the target. In your pool, each match scores:

- **3 points** for the exact scoreline (you said 2-1, it finished 2-1)
- **2 points** for the correct result *and* goal difference (you said 2-1, it finished 3-2 — right winner, right margin, wrong exact score)
- **1 point** for the correct result only (you said 2-1, it finished 3-0 — right winner, wrong margin)
- **0 points** otherwise

This one rule drives every design decision. It means the question is **not** "who will win?" but "**what exact score earns the most points on average?**" Those are different questions, and the gap between them is where the model earns its edge. The middle tier matters: it rewards getting the *margin* right, which pulls the picks toward one-goal results like 1-0, and it makes a 1-1 draw the best bet on the most evenly-matched games (every draw shares goal difference zero, so 1-1 banks 2 points on *any* draw). Hold that thought — it returns in Stage 3.

The whole pipeline has six stages:

```
INPUTS → CLEAN THE ODDS → PREDICT EACH MATCH → SIMULATE 200,000 TOURNAMENTS
        → OPTIMIZE THE BRACKET → CHECK THE RISK (machine learning)
```

---

## 1. Inputs — what goes in

Four datasets, all collected June 5–7, 2026 (four days before kickoff):

| Input | What it is | Why it matters |
|---|---|---|
| **Bookmaker odds** | bet365, FanDuel, Betfair, plus Polymarket & Kalshi prediction markets | The single best public estimate of each match's probabilities. Beating the betting market is *hard* — so we start from it. |
| **Elo ratings** | A single strength number per team (Spain 2165, Qatar 1423) | Needed where the market has no odds yet — especially hypothetical knockout matchups that haven't been drawn. |
| **Team news** | Confirmed injuries: Rodrygo (Brazil), Xavi Simons (Netherlands), Mitoma (Japan) out | Lets us nudge a team's strength down when a key player is missing. |
| **Tournament structure** | All 104 fixtures, venues, and the 48-team bracket rules | The bracket's wiring — including the tricky rule that 8 of 12 third-placed teams advance — is itself a major part of the problem. |

**Key idea:** the model is only as good as these inputs. Because the group-stage probabilities come *from* the betting market, the model can't be sharper than the market on any single match. Its edge comes entirely from two things it does *with* those probabilities: smart scoreline selection (Stage 3) and smart bracket routing (Stage 5).

---

## 2. Clean the odds — from prices to fair probabilities

Bookmakers don't publish true probabilities. Their odds include a hidden profit margin (the "vig"), so the implied probabilities add up to *more* than 100%.

**Example.** If the odds imply Home 50%, Draw 30%, Away 28%, that sums to 108% — the extra 8% is the bookmaker's built-in edge. We strip it by simple normalization: divide each by the total.

$$ p_{\text{fair}} = \frac{1/\text{odds}}{\sum (1/\text{odds})} $$

So 50/30/28 becomes 46/28/26, now summing to 100%. These are the **fair probabilities** we actually use.

For the ~24 matchday-3 fixtures with no published odds yet, we fall back to Elo-based estimates (the weakest data tier — we flag those honestly).

---

## 3. Predict each match — the Poisson scoreline model

This is the cleverest part, and the Netherlands–Japan example shows exactly why.

### The setup
Goals in football follow a **Poisson distribution** — a standard model for "how many rare events happen in a fixed time." Each team gets a goal *rate* called **lambda** ($\lambda$): the average number of goals we'd expect it to score. We find the two rates ($\lambda$ for each team) that reproduce the match's fair probabilities.

### Worked example: Netherlands vs Japan
- Fair probabilities from odds: **Netherlands 46% / Draw 26% / Japan 28%**
- The fitted rates that reproduce those: **$\lambda_{\text{NED}}$ = 1.5 goals, $\lambda_{\text{JPN}}$ = 1.1 goals**

From those two rates, we can compute the probability of *every* possible scoreline:

| Scoreline | Probability |
|---|---|
| **1-1** | **12.3%** ← most likely score overall |
| 1-0 | 11.1% |
| 2-1 | 9.2% |
| 2-0 | 8.4% |
| 0-1 | 8.2% |

### The crucial subtlety
Look closely: the single most likely scoreline is **1-1, a draw** — but the Netherlands is *favored to win* (46% vs 28%). If we naively predicted the most likely score (1-1), we'd be predicting a draw for a match we think the Netherlands wins. Under your scoring, that's a bad bet: we'd throw away the 1 outcome-point most of the time.

So the rule is: **pick the most likely scoreline *among the predicted outcome*.** The Netherlands is favored, so we look only at Netherlands-win scores and take the most likely one → **1-0**.

This is why almost all the picks are 1-0, 2-0, or 2-1: those are simply the most common winning scorelines in football. It's not timidity — it's the mathematically optimal play under "exact score beats outcome."

We checked this formally: across all 72 group matches, this rule produces the exact same pick as a brute-force expected-points maximizer in 71 of 72 cases.

### Knockouts: Elo win-expectancy
Hypothetical knockout matchups (e.g. "Spain vs Portugal in the Round of 16") have no betting odds — they haven't been drawn yet. For those we use the **Elo formula**, the same one chess uses:

$$ P(\text{A beats B}) = \frac{1}{1 + 10^{-(R_A - R_B)/400}} $$

A 100-point Elo gap ≈ 64% win chance; 200 points ≈ 76%. We adjust the ratings for injuries (Brazil −20 for Rodrygo) and home advantage (Mexico/USA +40 at their own stadiums).

---

## 4. Simulate the tournament 200,000 times

Now we have a probability for every possible match. But a tournament is a *chain* — who Spain plays in the quarter-final depends on dozens of earlier results. There's no formula for "who wins the World Cup." So we **simulate**.

**One simulation** = play the entire World Cup once:
1. For each of the 72 group matches, *roll the dice* using its fitted goal rates to get a random but realistic scoreline.
2. Tally the group tables (points, goal difference, goals scored), apply FIFA's tiebreakers, and rank the third-placed teams — the best 8 of 12 advance, slotted into the bracket by FIFA's official allocation table.
3. Play all 31 knockout matches as Elo-weighted coin flips (a 70% favorite wins 70% of the time, loses 30%).
4. Record who won, who reached each round, who played whom.

Then do that **200,000 times.** Because each run has different dice, you get a full distribution: Spain wins about 27% of the simulated tournaments, Argentina 18%, and so on — and crucially, you see *how often each team reaches each round*, and *which matchups actually tend to happen*.

**Why 200,000?** Statistical precision. With that many runs, each probability is accurate to about ±0.1 percentage point — fine enough that the numbers are stable, not simulation noise.

---

## 5. Optimize the bracket — "slot emergence"

This is the model's signature idea, and the **Portugal story** explains it best.

In a bracket pool you write *one team per slot*. Naively you'd write the stronger team. But a knockout pick only scores if that team **actually shows up in that slot**. And here's the trap:

- A *strong* team that often wins its group gets routed to **different bracket slots** depending on whether it finished 1st or 2nd. Its probability is *split* across slots.
- A *weaker but predictable* team that reliably finishes 2nd lands in **one specific slot** every time. Its probability is *concentrated*.

When you can only name one team per slot, the concentrated team is often the better bet — even if it's weaker — because it's more likely to be standing there when the match is played.

So instead of "who's stronger?", we ask the simulation: **"which team most often occupies AND wins this exact slot?"** That number is *slot emergence*, and we pick the team that maximizes it. This single criterion overturned three of our naive picks — and it's why your sheet has some calls (like Portugal running deep) that look surprising but are actually higher-scoring.

---

## 6. Check the risk — the machine learning layer

The simulation gives us 200,000 labeled examples ("these group results → this many of Avraa's picks were right"). That's a dataset, so we can ask a **Random Forest** and **XGBoost** (two standard machine-learning models): *which group results matter most to the final score?*

Two honest findings came out:

1. **Group-stage correctness explains only ~50% of your bracket score.** The other half is pure knockout luck that no forecast can control. Both models agree on this — it's not a fluke of one method.

2. **Not all group calls are equal.** Getting **Spain out of Group H** right is the single highest-leverage call — worth about **+0.8 points** on average, roughly three times the weakest group. Why? Because Spain's predicted path runs six matches deep, so if Spain *doesn't* top its group, your whole champion run collapses. The lesson: protect that one call above all.

(This ML layer is a *sensitivity analysis of our own simulation* — it tells us where our model's risk is concentrated. It's not an independent second forecast.)

---

## 7. Putting it together — the output

After all six stages, the model produces:

- **104 match predictions** — the exact scores filled into your submission sheet
- **Champion: Spain (27%)**, beating Argentina 1-0 in the final, France third
- **A full survival table** — every team's odds of reaching each round
- **A ranked risk list** — which results to watch, which calls to protect

And the honest headline that keeps it all in perspective: **even the most likely champion loses 73% of simulated tournaments.** The model doesn't predict the future — it finds the single set of guesses that, on average, scores the most points. Math gets you the edge; luck still decides the night.

---

## One-paragraph summary

We start from the betting market (the best public guess), clean it into fair probabilities, and turn each match into its most-likely-winning scoreline with a Poisson goal model. We fill knockout gaps with chess-style Elo ratings, then play the entire tournament 200,000 times to see the full range of what could happen. We pick each bracket slot by *who most often actually wins that slot*, not just who's stronger, and finally use machine learning to find where the biggest risks hide. The result is a complete, points-optimized sheet — and a clear-eyed sense of how much is skill and how much is luck.

*— Built by Avralt-Od Purevjav, June 7, 2026*
