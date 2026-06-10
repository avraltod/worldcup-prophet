"""Back out Colombia-Portugal match probabilities from the group-winner market.

Markets (Kalshi/Polymarket 2026-06-07): P(POR wins K) = .63, P(COL wins K) = .32
(normalized over the four teams: POR .624, COL .317, COD .040, UZB .020).
Find the Elo gap g (Portugal minus Colombia) such that simulating Group K
(other five fixtures kept at their current fitted rates) reproduces the
market's POR/COL group-winner ratio. Then emit the implied match probabilities
for the Colombia (home) vs Portugal fixture.
"""
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import GROUP_FIXTURES
from poisson_model import fit_rates, pois, MAX_G

DATA = Path(__file__).parent.parent / "data"
N = 40000

preds = json.loads((DATA / "group_predictions.json").read_text())
RATES = {}
for p in preds:
    if p["group"] != "K":
        continue
    ph, pd, pa = p["p"]
    s = ph + pd + pa
    RATES[p["row"]] = (*fit_rates(ph / s, pd / s, pa / s), p["home"], p["away"])

K_ROWS = [r for r, g, h, a in GROUP_FIXTURES if g == "K"]
COLPOR_ROW = 68  # Colombia (home) vs Portugal


def colpor_probs(gap):
    """Match probs for Colombia vs Portugal given Portugal Elo edge `gap`."""
    e_col = 1 / (1 + 10 ** (gap / 400))           # P(Colombia 'wins' incl. draw share)
    pd_ = 0.29 * math.exp(-abs(gap) / 700)
    ph = max(0.02, e_col - pd_ / 2)
    pa = max(0.02, 1 - ph - pd_)
    s = ph + pd_ + pa
    return ph / s, pd_ / s, pa / s


def sim_group_winner(gap, n=N):
    random.seed(7)
    ph, pd_, pa = colpor_probs(gap)
    lh, la = fit_rates(ph, pd_, pa)
    rates = dict(RATES)
    rates[COLPOR_ROW] = (lh, la, "Colombia", "Portugal")

    def sample(lam):
        r, acc = random.random(), 0.0
        for k in range(MAX_G + 1):
            acc += pois(k, lam)
            if r <= acc:
                return k
        return MAX_G

    wins = defaultdict(int)
    for _ in range(n):
        stats = defaultdict(lambda: [0, 0, 0])
        for row in K_ROWS:
            lh_, la_, home, away = rates[row]
            hg, ag = sample(lh_), sample(la_)
            for t, f, g in ((home, hg, ag), (away, ag, hg)):
                stats[t][1] += f - g
                stats[t][2] += f
                stats[t][0] += 3 if f > g else (1 if f == g else 0)
        top = max(stats, key=lambda t: (*stats[t], random.random()))
        wins[top] += 1
    return {t: c / n for t, c in wins.items()}, (ph, pd_, pa)


target = 0.624 / 0.317  # market POR/COL ratio ~1.97
print(f"market target: P(POR K1)/P(COL K1) = {target:.2f}")
print(f"{'gap':>5} {'pPOR_K1':>8} {'pCOL_K1':>8} {'ratio':>6}   COL-POR match p(H/D/A)")
best, best_err = None, 9e9
for gap in range(0, 161, 20):
    w, probs = sim_group_winner(gap)
    r = w.get("Portugal", 0) / max(w.get("Colombia", 1e-9), 1e-9)
    err = abs(r - target)
    if err < best_err:
        best, best_err = (gap, w, probs), err
    print(f"{gap:>5} {w.get('Portugal',0):>8.3f} {w.get('Colombia',0):>8.3f} "
          f"{r:>6.2f}   ({probs[0]:.3f}, {probs[1]:.3f}, {probs[2]:.3f})")
gap, w, probs = best
print(f"\nBEST: gap={gap} -> POR K1 {w.get('Portugal',0):.3f}, COL K1 "
      f"{w.get('Colombia',0):.3f}; Colombia-Portugal match p(H/D/A) = "
      f"({probs[0]:.3f}, {probs[1]:.3f}, {probs[2]:.3f})")
