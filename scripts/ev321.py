"""EV-optimal scoreline under the pool's 3/2/1 rule.

Points: 3 for the exact score, 2 for the correct result AND goal difference (not
exact), 1 for the correct result only. The expected value of a prediction (h,a)
simplifies to P(exact) + P(result & goal difference) + P(result), and the optimal
pick maximizes it. Draws become competitive on even matches because every draw
shares goal difference zero, so a 1-1 prediction collects the 2-point tier on
every drawn outcome.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from poisson_model import pois, MAX_G


def ev_321(h, a, lh, la):
    gp = h - a
    rp = (h > a) - (h < a)
    p_exact = pois(h, lh) * pois(a, la)
    p_rg = p_r = 0.0
    for i in range(MAX_G + 1):
        for j in range(MAX_G + 1):
            p = pois(i, lh) * pois(j, la)
            r = (i > j) - (i < j)
            if r == rp:
                p_r += p
                if i - j == gp:
                    p_rg += p
    return p_exact + p_rg + p_r


def best_pick(lh, la):
    best, bev = (1, 0), -1.0
    for h in range(MAX_G + 1):
        for a in range(MAX_G + 1):
            ev = ev_321(h, a, lh, la)
            if ev > bev:
                best, bev = (h, a), ev
    return best
