"""Snapshot helpers for the forecast trajectory. kl_divergence measures the
information (in bits) between two champion distributions -- how much a game
moved the forecast."""
import math


def kl_divergence(p, q, eps=1e-12):
    """KL(p || q) in bits over champion distributions {team: prob}. Terms with
    p[t] == 0 contribute nothing; q[t] is floored at eps to avoid div-by-zero."""
    total = 0.0
    for team, pt in p.items():
        if pt > 0:
            qt = max(q.get(team, 0.0), eps)
            total += pt * math.log2(pt / qt)
    return total
