"""Narrative analysis content for the prediction paper (group + knockout)."""

GROUP_ANALYSIS = {
 "A": "**Why:** Mexico is the clearest host-advantage story in the draw — opener at the Azteca (2,240 m altitude), ~68% market favorite, Jiménez in form. Second place is a genuine coin flip: South Korea over Czechia on Elo (1756 vs 1733) and tournament pedigree; their opener effectively decides it. Czechia still advances as a third-placer.",
 "B": "**Why:** Switzerland is the quiet Elo monster (1894 — above Belgium). Canada gets host energy but the head-to-head tilts Swiss (50% vs 30%). Qatar is the weakest team in the field (Elo 1423) — everyone farms them for goal difference. Bosnia's win over Qatar books a third-place ticket.",
 "C": "**Why:** Brazil tops the group even without Rodrygo (ACL) and with Neymar's calf in doubt — Elo 1988 absorbs it. The pivotal game is Scotland–Morocco for second: the market is decisive (Morocco 50% vs 23%). Scotland's 3 points die on goal difference in the third-place table.",
 "D": "**Why:** The tightest group in the tournament. Turkey has the higher Elo (1906), but the USA has host advantage and the market's blessing (group-winner: USA 40%, Turkey 35%); their head-to-head priced at a literal 36.3/36.3 tie, broken toward the USA because simulations show it routes both teams into safer bracket slots. Paraguay (Elo 1833, underrated) advances third.",
 "E": "**Why:** Germany–Curaçao is the heaviest mismatch of the tournament (92% — hence the 3-0). Ecuador's Elo (1935) is higher than Uruguay's or Croatia's — an elite team hiding behind low name recognition; they beat Ivory Coast in the decider (42% vs 28%). Ivory Coast still advances as one of the two best third-placers.",
 "F": "**Why:** Decided on day one — Netherlands–Japan is the marquee group game (46% vs 28%). The Dutch absorb the Xavi Simons ACL loss; Japan miss Mitoma's wing threat but still take second comfortably. Sweden's win over Tunisia is worth a third-place ticket.",
 "G": "**Why:** The weakest group on paper. Belgium (1866) wins it without being impressive — which is exactly why the simulations love their bracket path. Egypt–Iran decides second (42% vs 27%, Salah's last World Cup vs Iran's organized block). Iran advances third.",
 "H": "**Why:** The champion's runway. Spain is the highest-rated team in the field (Elo 2165), Yamal's fitness trending right, 85%+ market favorite in two of three games. Bielsa's healthy Uruguay is a rock-solid second. Cape Verde's fairytale ends at 3 points, GD −2.",
 "I": "**Why:** France tops it (66% market) despite the odd friendly loss — depth absorbs anything. The story is Norway: first World Cup since 1998, Haaland fit, clear seconds (24% group-winner vs Senegal's 10%); Norway–Senegal on matchday 2 is the real final. Senegal advances as the strongest third-placer in the tournament — which is why Portugal drawing them in the R32 matters.",
 "J": "**Why:** The defending champions stroll — Argentina's Elo (2113) towers here, Messi's hamstring managed. Austria is Europe's stealth team (Rangnick-built pressing) and beats Algeria in the decider (43% vs 28%). Algeria's win over Jordan secures third place.",
 "K": "**Why:** The group rewritten on deadline day. Raw Elo called Portugal–Colombia a dead tie; the prediction markets said Portugal 63% / Colombia 32% to win the group — so the model was recalibrated (140 Elo-equivalent points) and Portugal now tops it via a 1-0 in the head-to-head. This single call transforms Portugal's tournament from R32 exit to QF run. The biggest known sensitivity in the bracket.",
 "L": "**Why:** England dominates (68% market, no injuries) — and that reliability quietly powers the bracket: because England nearly always wins Group L, Croatia nearly always lands second, which is why Croatia owns its R32 slot. Modrić's farewell squad is in poor warm-up form (−10 rating) but still outclasses Ghana and Panama.",
}

KO_ANALYSIS = {
 "Round of 32 — June 28 to July 3":
  "**Logic of this round:** every pick maximizes *slot emergence* — the probability the named team actually occupies and wins that bracket slot across 200,000 simulations — not just head-to-head strength. Three picks deliberately go against the head-to-head favorite: **Norway over Ecuador** (Norway's path to the slot is far more reliable, +4pp), **Croatia over Colombia** (England's dominance parks Croatia in this slot with high certainty), and the structural calls around Group D. Portugal's M87 emergence (50.7%) is the strongest slot claim in the entire bracket. Mexico at the Azteca and the USA in Arlington carry host bonuses.",
 "Round of 16 — July 4 to 7":
  "**Key calls:** France ends Germany (Elo 2081 vs 1925 — a quarter-final-quality tie too early). **Belgium over the USA** was the simulations' biggest correction (+9.6pp): Belgium's soft path through Group G makes them far likelier to even be here than any Group D survivor. England eliminates host Mexico at the Azteca — atmosphere loses to Elo gap (2020 vs 1908). Brazil handles Haaland's Norway; Spain ends Croatia; Portugal beats Switzerland in the slot the market opened for him.",
 "Quarter-finals — July 9 to 11":
  "**Key calls:** France–Netherlands is the closest QF (56/19/25) — French depth decides it. Spain dispatches Belgium (71%). **England over Brazil** is the boldest call of the bracket: a 44/28 market edge for England plus Brazil's Rodrygo/Neymar injuries; this is where the sheet wins or loses its swagger. Argentina ends Portugal's run (38% vs 21% slot emergence) — Messi vs Ronaldo's heirs, one last time.",
 "Semi-finals — July 14 & 15":
  "**Key calls:** Spain over France (48% vs 25% in the matchup) — the two best teams meet one round early; Spain's midfield control beats French transition. Argentina over England (50% vs 24%): tournament know-how against a team that historically blinks in semis.",
 "Third place — July 18":
  "**Why France:** the third-place game rewards squad depth and motivation management — France has more of both than England (45/27/28).",
 "FINAL — July 19, MetLife Stadium":
  "**Why Spain:** the most likely final (10.8% of all simulations — no other pairing scores higher) and the most likely champion (27.4%). Spain beats Argentina in 59% of simulated finals: the Elo gap (2160 vs 2113 adjusted), a younger core, and the deepest midfield in the tournament. Predicted score 1-0 — the modal scoreline at 13.2%. Honesty box: Spain still fails to win 72.6% of simulated tournaments; this is the best single bet, not a promise.",
}

DIARY_INTRO = """## Tournament Diary — What Went Wrong & What We Learned

*Predictions above are locked (before the June 11 kickoff). This diary tracks reality against the model after each matchday: points earned, calls that broke, and the updated outlook. The picks never change — the understanding does.*

| Date | Matches | Pts won / possible | What went wrong (or right) | Bracket implications |
|------|---------|-------------------|---------------------------|---------------------|
"""

DIARY_DAYS = [
    "Jun 11", "Jun 12", "Jun 13", "Jun 14", "Jun 15", "Jun 16", "Jun 17",
    "Jun 18", "Jun 19", "Jun 20", "Jun 21", "Jun 22", "Jun 23", "Jun 24",
    "Jun 25", "Jun 26", "Jun 27", "— R32 Jun 28–Jul 3", "— R16 Jul 4–7",
    "— QF Jul 9–11", "— SF Jul 14–15", "— Final Jul 18–19",
]
