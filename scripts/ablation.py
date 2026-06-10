"""Ablation waterfall: cumulative factor decomposition of the forecast.

M0  raw Elo everywhere (group rates from Elo, no adjustments, no host)
M1  + market odds tier for group matches (the June 5-7 collected rates)
M2  + injury adjustments (BRA -20, NED -15, JPN -10, CRO -10, ESP -5)
M3  + host advantage (MEX/USA/CAN +40, +20 late)
M4  + Group K market recalibration (POR/COL gap 140)  == submitted model

Reports champion probabilities and P(Portugal wins Group K) per rung.
N=20,000 per rung (champion SE ~0.3pp). Order is chronological-by-construction;
contributions are order-dependent (stated in the paper).
"""
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import GROUP_FIXTURES
from poisson_model import fit_rates, pois, MAX_G

DATA = Path(__file__).parent.parent / "data"
N = 20000

info = json.loads((DATA / "elo_outright_news.json").read_text())
ELO = {t["team"]: t["elo"] for t in info["elo"]}
INJ = dict(info["injury_elo_adj"])

PRED_V1 = json.loads((DATA / "group_predictions_v1_backup.json").read_text())
PRED_V2 = json.loads((DATA / "group_predictions.json").read_text())


def elo_match_probs(h, a):
    d = ELO[h] - ELO[a]
    e = 1 / (1 + 10 ** (-d / 400))
    pd_ = 0.30 * math.exp(-abs(d) / 700)
    ph = max(0.02, e - pd_ / 2)
    pa = max(0.02, 1 - ph - pd_)
    s = ph + pd_ + pa
    return ph / s, pd_ / s, pa / s


def build_rates(source):
    rates = {}
    if source == "elo":
        for row, grp, h, a in GROUP_FIXTURES:
            ph, pd_, pa = elo_match_probs(h, a)
            rates[row] = (*fit_rates(ph, pd_, pa), h, a)
    else:
        preds = PRED_V1 if source == "market_v1" else PRED_V2
        for p in preds:
            ph, pd_, pa = p["p"]
            s = ph + pd_ + pa
            rates[p["row"]] = (*fit_rates(ph / s, pd_ / s, pa / s), p["home"], p["away"])
    return rates


GROUPS = defaultdict(list)
for row, grp, h, a in GROUP_FIXTURES:
    GROUPS[grp].append(row)
TS = {74: set("ABCDF"), 77: set("CDFGH"), 81: set("BEFIJ"), 82: set("AEHIJ"),
      79: set("CEFHI"), 80: set("EHIJK"), 85: set("EFGIJ"), 87: set("DEIJL")}
SO = list(TS)
R32 = {74: ("E1", "T74"), 77: ("I1", "T77"), 73: ("A2", "B2"), 75: ("F1", "C2"),
       76: ("C1", "F2"), 78: ("E2", "I2"), 79: ("A1", "T79"), 80: ("L1", "T80"),
       83: ("K2", "L2"), 84: ("H1", "J2"), 81: ("D1", "T81"), 82: ("G1", "T82"),
       86: ("J1", "H2"), 88: ("D2", "G2"), 85: ("B1", "T85"), 87: ("K1", "T87")}
R16 = {89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
       93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87)}
QF = {97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96)}
SF = {101: (97, 98), 102: (99, 100)}


def run(rates, inj_scale, host, host_late, recal):
    random.seed(2026)
    adj = {t: inj_scale * v for t, v in INJ.items()}
    if recal:
        adj["Portugal"] = adj.get("Portugal", 0) + 66
        adj["Colombia"] = adj.get("Colombia", 0) - 67
    hosts = {"Mexico": host, "United States": host, "Canada": host}
    hosts_late = {k: host_late for k in hosts}

    def rating(t, late=False):
        hm = hosts_late if late else hosts
        return ELO[t] + adj.get(t, 0) + hm.get(t, 0)

    def kw(a, b, late=False):
        e = 1 / (1 + 10 ** (-(rating(a, late) - rating(b, late)) / 400))
        return a if random.random() < e else b

    def sample(lam):
        r, acc = random.random(), 0.0
        for k in range(MAX_G + 1):
            acc += pois(k, lam)
            if r <= acc:
                return k
        return MAX_G

    def assign(q):
        def bt(i, used):
            if i == len(SO):
                return {}
            c = [g for g in q if g not in used and g in TS[SO[i]]]
            random.shuffle(c)
            for g in c:
                r = bt(i + 1, used | {g})
                if r is not None:
                    r[SO[i]] = g
                    return r
            return None
        return bt(0, set())

    champ = Counter()
    k1_por = 0
    for _ in range(N):
        pos, thirds = {}, {}
        for grp in "ABCDEFGHIJKL":
            st = defaultdict(lambda: [0, 0, 0])
            for row in GROUPS[grp]:
                lh, la, h, a = rates[row]
                hg, ag = sample(lh), sample(la)
                for t, f, g_ in ((h, hg, ag), (a, ag, hg)):
                    st[t][1] += f - g_
                    st[t][2] += f
                    st[t][0] += 3 if f > g_ else (1 if f == g_ else 0)
            o = sorted(st, key=lambda t: (*st[t], random.random()), reverse=True)
            pos[f"{grp}1"], pos[f"{grp}2"] = o[0], o[1]
            thirds[grp] = (o[2], tuple(st[o[2]]))
        if pos["K1"] == "Portugal":
            k1_por += 1
        rk = sorted(thirds, key=lambda g: (*thirds[g][1], random.random()), reverse=True)
        am = assign(rk[:8]) or assign(rk[:7] + [rk[8]])
        if am is None:
            continue
        slots = dict(pos)
        for m, g_ in am.items():
            slots[f"T{m}"] = thirds[g_][0]
        W = {}
        for m, (s1, s2) in R32.items():
            W[m] = kw(slots[s1], slots[s2])
        for tab, late in ((R16, False), (QF, True), (SF, True)):
            for m, (m1, m2) in tab.items():
                W[m] = kw(W[m1], W[m2], late)
        champ[kw(W[101], W[102], True)] += 1
    teams = ["Spain", "Argentina", "France", "Portugal", "England", "Brazil", "Mexico"]
    return {t: 100 * champ[t] / N for t in teams}, 100 * k1_por / N


RUNGS = [
    ("M0 raw Elo only",        "elo",        0.0, 0,  0,  False),
    ("M1 + market group odds", "market_v1",  0.0, 0,  0,  False),
    ("M2 + injuries",          "market_v1",  1.0, 0,  0,  False),
    ("M3 + host advantage",    "market_v1",  1.0, 40, 20, False),
    ("M4 + Group K recal",     "market_v2",  1.0, 40, 20, True),
]

print(f"{'rung':<26} {'Spain':>6} {'Arg':>6} {'Fra':>6} {'Por':>6} {'Eng':>6} "
      f"{'Bra':>6} {'Mex':>6} | {'P(POR K1)':>9}")
prev = None
for label, src, inj, h, hl, rc in RUNGS:
    rates = build_rates(src)
    res, k1 = run(rates, inj, h, hl, rc)
    row = f"{label:<26}" + "".join(f" {res[t]:>5.1f}" for t in
        ["Spain", "Argentina", "France", "Portugal", "England", "Brazil", "Mexico"])
    print(f"{row} | {k1:>8.1f}%")
    if prev:
        d = " ".join(f"{t[:3]}{res[t]-prev[t]:+.1f}" for t in res if abs(res[t]-prev[t]) >= 0.3)
        print(f"  {'Δ vs previous:':<24} {d}")
    prev = res
