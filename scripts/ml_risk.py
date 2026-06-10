"""Random-Forest global sensitivity analysis of the submitted bracket's risk.

Each simulated tournament is one example. Features encode group-stage outcomes
(which team won each group, which finished second). The target is the number of
the 31 submitted knockout picks whose named team actually occupies and wins its
slot in that tournament. A Random Forest then attributes the variance in that
score to specific group outcomes, so permutation importance answers: which group
results most swing the submitted bracket's success?

This is a surrogate analysis of the simulation, not an independent forecast.
"""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import GROUP_FIXTURES

DATA = Path(__file__).parent.parent / "data"
N = 40000
random.seed(7)

info = json.loads((DATA / "elo_outright_news.json").read_text())
ELO = {t["team"]: t["elo"] for t in info["elo"]}
ADJ = dict(info["injury_elo_adj"])
ADJ["Portugal"] = ADJ.get("Portugal", 0) + 66
ADJ["Colombia"] = ADJ.get("Colombia", 0) - 67
HOSTS = {"Mexico", "United States", "Canada"}

from poisson_model import fit_rates, pois, MAX_G
preds = json.loads((DATA / "group_predictions.json").read_text())
MR = {}
for p in preds:
    ph, pd, pa = p["p"]
    s = ph + pd + pa
    MR[p["row"]] = (*fit_rates(ph / s, pd / s, pa / s), p["home"], p["away"])
GROUPS = defaultdict(list)
TEAMS = defaultdict(list)
for row, grp, h, a in GROUP_FIXTURES:
    GROUPS[grp].append(row)
    for t in (h, a):
        if t not in TEAMS[grp]:
            TEAMS[grp].append(t)

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

# Submitted picks: the team Avraa entered as the winner of each knockout slot.
PICK = {74: "Germany", 77: "France", 73: "Canada", 75: "Netherlands",
        76: "Brazil", 78: "Norway", 79: "Mexico", 80: "England",
        83: "Croatia", 84: "Spain", 81: "United States", 82: "Belgium",
        86: "Argentina", 88: "Turkey", 85: "Switzerland", 87: "Portugal",
        89: "France", 90: "Netherlands", 91: "Brazil", 92: "England",
        93: "Spain", 94: "Belgium", 95: "Argentina", 96: "Portugal",
        97: "France", 98: "Spain", 99: "England", 100: "Argentina",
        101: "Spain", 102: "Argentina", 104: "Spain"}


def rating(t, late=False):
    return ELO[t] + ADJ.get(t, 0) + ((20 if late else 40) if t in HOSTS else 0)


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


# Feature columns: for each group, "winner == predicted winner" and
# "runner-up == predicted runner-up" (binary), plus champion-relevant flags.
PRED_WIN = {g: None for g in "ABCDEFGHIJKL"}
PRED_2ND = {g: None for g in "ABCDEFGHIJKL"}
# derive predicted group order from the submitted scorelines
gp = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
for p in preds:
    g = p["group"]
    for t, f, a in ((p["home"], p["hg"], p["ag"]), (p["away"], p["ag"], p["hg"])):
        gp[g][t][0] += 3 if f > a else (1 if f == a else 0)
        gp[g][t][1] += f - a
        gp[g][t][2] += f
for g in "ABCDEFGHIJKL":
    order = sorted(gp[g], key=lambda t: tuple(gp[g][t]), reverse=True)
    PRED_WIN[g], PRED_2ND[g] = order[0], order[1]

feat_names = [f"{g}: winner correct" for g in "ABCDEFGHIJKL"] + \
             [f"{g}: runner-up correct" for g in "ABCDEFGHIJKL"]
X, y = [], []
for _ in range(N):
    pos, thirds = {}, {}
    win_ok, sec_ok = {}, {}
    for grp in "ABCDEFGHIJKL":
        st = defaultdict(lambda: [0, 0, 0])
        for row in GROUPS[grp]:
            lh, la, h, a = MR[row]
            hg, ag = sample(lh), sample(la)
            for t, f, g_ in ((h, hg, ag), (a, ag, hg)):
                st[t][1] += f - g_
                st[t][2] += f
                st[t][0] += 3 if f > g_ else (1 if f == g_ else 0)
        o = sorted(st, key=lambda t: (*st[t], random.random()), reverse=True)
        pos[f"{grp}1"], pos[f"{grp}2"] = o[0], o[1]
        thirds[grp] = (o[2], tuple(st[o[2]]))
        win_ok[grp] = int(o[0] == PRED_WIN[grp])
        sec_ok[grp] = int(o[1] == PRED_2ND[grp])
    rk = sorted(thirds, key=lambda g: (*thirds[g][1], random.random()), reverse=True)
    am = assign(rk[:8]) or assign(rk[:7] + [rk[8]])
    if am is None:
        continue
    slots = dict(pos)
    for m, g_ in am.items():
        slots[f"T{m}"] = thirds[g_][0]
    W = {}
    score = 0
    for m, (s1, s2) in R32.items():
        W[m] = kw(slots[s1], slots[s2])
        if W[m] == PICK[m]:
            score += 1
    for tab, late in ((R16, False), (QF, True), (SF, True)):
        for m, (m1, m2) in tab.items():
            W[m] = kw(W[m1], W[m2], late)
            if W[m] == PICK[m]:
                score += 1
    champ = kw(W[101], W[102], True)
    if champ == PICK[104]:
        score += 1
    X.append([win_ok[g] for g in "ABCDEFGHIJKL"] +
             [sec_ok[g] for g in "ABCDEFGHIJKL"])
    y.append(score)

X = np.array(X)
y = np.array(y)
print(f"dataset: {X.shape[0]} sims, {X.shape[1]} features; "
      f"target (correct KO picks of 31) mean={y.mean():.2f} sd={y.std():.2f} "
      f"max={y.max()}")

Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=0)
rf = RandomForestRegressor(n_estimators=300, max_depth=12, min_samples_leaf=20,
                           n_jobs=-1, random_state=0)
rf.fit(Xtr, ytr)
r2 = rf.score(Xte, yte)
print(f"RF test R^2 = {r2:.3f}")

pi = permutation_importance(rf, Xte, yte, n_repeats=10, random_state=0, n_jobs=-1)
order = np.argsort(pi.importances_mean)[::-1]
print("\nTop risk drivers (permutation importance, drop in R^2-units of variance):")
results = []
for i in order[:14]:
    print(f"  {feat_names[i]:<24} {pi.importances_mean[i]:.4f} "
          f"(impurity {rf.feature_importances_[i]:.3f})")
    results.append({"feature": feat_names[i],
                    "perm_importance": round(float(pi.importances_mean[i]), 4),
                    "impurity_importance": round(float(rf.feature_importances_[i]), 4)})
json.dump({"r2": round(float(r2), 3), "n": int(X.shape[0]),
           "target_mean": round(float(y.mean()), 3),
           "drivers": results}, open(DATA / "ml_risk.json", "w"), indent=1)
