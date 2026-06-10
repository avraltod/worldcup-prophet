"""Improvement #1: in-tournament Bayesian (Elo) updating.

Does letting the model learn from results as the tournament unfolds improve its
prediction of later matches? Process each 2018/2022 match in order; predict it
with the CURRENT ratings, then update both teams' Elo by the standard rule with a
goal-difference multiplier. Compare the adaptive forecast to the frozen
pre-tournament forecast, reported separately for the group stage and the
knockouts (where learning has had time to act).
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

DATA = Path(__file__).parent.parent / "data" / "backtest"
ALIAS = {"United States": "USA"}
HOSTS = {2018: "Russia", 2022: "Qatar"}


def winexp(ra, rb):
    return 1 / (1 + 10 ** (-(ra - rb) / 400))


def hda(ra, rb):
    d = ra - rb
    e = 1 / (1 + 10 ** (-d / 400))
    pd = 0.30 * math.exp(-abs(d) / 700)
    ph = max(.01, e - pd / 2)
    pa = max(.01, 1 - ph - pd)
    s = ph + pd + pa
    return {"H": ph / s, "D": pd / s, "A": pa / s}


def outcome(h, a):
    return "H" if h > a else ("D" if h == a else "A")


def brier(p, real):
    return sum((p[o] - (1.0 if o == real else 0.0)) ** 2 for o in "HDA")


def gd_mult(gd):
    g = abs(gd)
    if g <= 1:
        return 1.0
    if g == 2:
        return 1.5
    return (11 + g) / 8


def run(year, K):
    elo0 = json.loads((DATA / f"elo_{year}.json").read_text())
    res = json.loads((DATA / f"results_{year}.json").read_text())
    host = HOSTS[year]

    def look(t):
        return elo0.get(t, elo0.get(ALIAS.get(t, t)))

    def norm(t):
        return t if look(t) is not None else ALIAS.get(t, t)

    frozen = {norm(m["home"]): look(m["home"]) for m in res if look(m["home"]) is not None}
    frozen.update({norm(m["away"]): look(m["away"]) for m in res if look(m["away"]) is not None})
    live = dict(frozen)

    out = {"group": [0.0, 0], "ko": [0.0, 0]}        # frozen brier
    outL = {"group": [0.0, 0], "ko": [0.0, 0]}       # adaptive brier
    for idx, m in enumerate(res):
        h, a = norm(m["home"]), norm(m["away"])
        if h not in frozen or a not in frozen:
            continue
        stage = "group" if idx < 48 else "ko"
        hb = 40 if h == host else 0
        ab = 40 if a == host else 0
        real = outcome(m["hg"], m["ag"])
        pf = hda(frozen[h] + hb, frozen[a] + ab)
        pl = hda(live[h] + hb, live[a] + ab)
        out[stage][0] += brier(pf, real); out[stage][1] += 1
        outL[stage][0] += brier(pl, real); outL[stage][1] += 1
        # update live ratings (Elo with GD multiplier)
        e = winexp(live[h] + hb, live[a] + ab)
        sc = 1.0 if m["hg"] > m["ag"] else (0.5 if m["hg"] == m["ag"] else 0.0)
        delta = K * gd_mult(m["hg"] - m["ag"]) * (sc - e)
        live[h] += delta
        live[a] -= delta
    return out, outL


if __name__ == "__main__":
    print("=== #1 In-tournament updating: frozen vs adaptive (Brier, lower is better) ===\n")
    for K in (0, 20, 30, 40, 60):
        agg = {"gf": [0, 0], "kf": [0, 0], "gl": [0, 0], "kl": [0, 0]}
        for year in (2018, 2022):
            out, outL = run(year, K)
            agg["gf"][0] += out["group"][0]; agg["gf"][1] += out["group"][1]
            agg["kf"][0] += out["ko"][0]; agg["kf"][1] += out["ko"][1]
            agg["gl"][0] += outL["group"][0]; agg["gl"][1] += outL["group"][1]
            agg["kl"][0] += outL["ko"][0]; agg["kl"][1] += outL["ko"][1]
        gf = agg["gf"][0] / agg["gf"][1]
        kf = agg["kf"][0] / agg["kf"][1]
        gl = agg["gl"][0] / agg["gl"][1]
        kl = agg["kl"][0] / agg["kl"][1]
        if K == 0:
            print(f"  frozen baseline:  group {gf:.3f}   knockouts {kf:.3f}")
            base_k = kf
        else:
            print(f"  K={K:>2}: adaptive group {gl:.3f}  knockouts {kl:.3f}  "
                  f"(knockout {'+' if kl<base_k else ''}{(base_k-kl)/base_k*100:.1f}% vs frozen)")
