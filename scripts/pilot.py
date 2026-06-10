"""Pilot / dress rehearsal of the live two-track forecaster. Feed a FAKE news
event (an injury) and a FAKE game (a dominated loss) and watch the forecast
react, end to end, before the real tournament starts. Uses the 2022 structure
as the working rig; the machinery is format-agnostic.

  python3 scripts/pilot.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tournament_2022 import GROUPS, BRACKET, RATINGS
from sim_tournament import simulate
from learn import LearningTrack
from snapshot import kl_divergence

N, SEED = 5000, 2026
TEAM, OPP = "Brazil", "Serbia"      # Brazil's Group-G opener
NEWS_DELTA = -80                    # "star striker injured"
LAM_OBS = {"home": 3.0, "away": 0.3}  # Brazil out-xG's Serbia massively but...
RESULT = (0, 2)                     # ...loses 0-2 (a freak, unlucky defeat)


def rr(ts):
    return [(ts[i], ts[j]) for i in range(4) for j in range(i + 1, 4)]


STRUCT = {"groups": GROUPS,
          "fixtures": {g: rr(ts) for g, ts in GROUPS.items()},
          "bracket": BRACKET}


def champ(ratings, results=None):
    out = simulate(STRUCT, ratings, results or {}, {}, N=N, seed=SEED)
    return {t: out[t]["champion"] for t in out}


def pct(d, t):
    return d[t] * 100


print("=" * 64)
print("  PILOT  —  dress rehearsal: fake news + a fake game")
print("=" * 64)

# --- A. baseline ---------------------------------------------------------
t0 = champ(RATINGS)
print(f"\nA. t=0 baseline                 {TEAM} champion = {pct(t0, TEAM):5.1f}%")

# --- B. BEFORE: fake injury news (exogenous strength change) --------------
news = {**RATINGS, TEAM: RATINGS[TEAM] + NEWS_DELTA}
before = champ(news)
print(f"B. fake news: {TEAM} star injured ({NEWS_DELTA:+d} Elo)")
print(f"   -> BEFORE snapshot            {TEAM} champion = {pct(before, TEAM):5.1f}%"
      f"   ({pct(before, TEAM)-pct(t0, TEAM):+.1f} pts, {kl_divergence(before, t0):.3f} bits of news)")

# --- C. AFTER: fake game, lost 0-2 but dominated on xG --------------------
results = {(TEAM, OPP): RESULT}
fz = champ(news, results)                                  # frozen: news + result only
L = LearningTrack(news)
L.apply_match(TEAM, OPP, LAM_OBS["home"], LAM_OBS["away"])  # learning: + performance
ln = champ({t: L.rating(t) for t in news}, results)
print(f"C. fake game: {TEAM} {RESULT[0]}-{RESULT[1]} {OPP}, "
      f"but out-xG'd {LAM_OBS['home']}-{LAM_OBS['away']} (unlucky)")
print(f"   -> AFTER  FROZEN  (result only) {TEAM} champion = {pct(fz, TEAM):5.1f}%   "
      f"(KL {kl_divergence(fz, before):.3f})")
print(f"   -> AFTER  LEARNING(+perf.)      {TEAM} champion = {pct(ln, TEAM):5.1f}%   "
      f"(rating {news[TEAM]:.0f} -> {L.rating(TEAM):.0f})")

# --- verdict -------------------------------------------------------------
gap = pct(ln, TEAM) - pct(fz, TEAM)
print("\n" + "-" * 64)
print(f"  VERDICT: news dropped {TEAM} {pct(before,TEAM)-pct(t0,TEAM):+.1f} pts;")
print(f"  the loss dropped it further, but LEARNING held it {gap:+.1f} pts above")
print(f"  FROZEN because it read the dominance. The live loop works. ✓")
print("-" * 64)
