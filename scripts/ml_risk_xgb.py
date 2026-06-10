"""XGBoost gradient-boosting companion to ml_risk.py.

Rebuilds the same surrogate dataset (group-stage correctness -> knockout score),
fits XGBoost alongside Random Forest as a robustness check on the importance
ranking, and uses SHAP for directional attribution (does a correct group call
raise or lower the entry's expected score, and by how much).
"""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import xgboost as xgb
import shap

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import GROUP_FIXTURES
from poisson_model import fit_rates, pois, MAX_G

DATA = Path(__file__).parent.parent / "data"
N = 40000
random.seed(7)

info = json.loads((DATA / "elo_outright_news.json").read_text())
ELO = {t["team"]: t["elo"] for t in info["elo"]}
ADJ = dict(info["injury_elo_adj"])
ADJ["Portugal"] = ADJ.get("Portugal", 0) + 66
ADJ["Colombia"] = ADJ.get("Colombia", 0) - 67
HOSTS = {"Mexico", "United States", "Canada"}

preds = json.loads((DATA / "group_predictions.json").read_text())
MR = {}
for p in preds:
    ph, pd, pa = p["p"]
    s = ph + pd + pa
    MR[p["row"]] = (*fit_rates(ph / s, pd / s, pa / s), p["home"], p["away"])
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


gp = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
for p in preds:
    g = p["group"]
    for t, f, a in ((p["home"], p["hg"], p["ag"]), (p["away"], p["ag"], p["hg"])):
        gp[g][t][0] += 3 if f > a else (1 if f == a else 0)
        gp[g][t][1] += f - a
        gp[g][t][2] += f
PRED_WIN, PRED_2ND = {}, {}
for g in "ABCDEFGHIJKL":
    o = sorted(gp[g], key=lambda t: tuple(gp[g][t]), reverse=True)
    PRED_WIN[g], PRED_2ND[g] = o[0], o[1]

feat = [f"{g}: winner correct" for g in "ABCDEFGHIJKL"] + \
       [f"{g}: runner-up correct" for g in "ABCDEFGHIJKL"]
X, y = [], []
for _ in range(N):
    pos, thirds, wok, sok = {}, {}, {}, {}
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
        wok[grp] = int(o[0] == PRED_WIN[grp])
        sok[grp] = int(o[1] == PRED_2ND[grp])
    rk = sorted(thirds, key=lambda g: (*thirds[g][1], random.random()), reverse=True)
    am = assign(rk[:8]) or assign(rk[:7] + [rk[8]])
    if am is None:
        continue
    slots = dict(pos)
    for m, g_ in am.items():
        slots[f"T{m}"] = thirds[g_][0]
    W, score = {}, 0
    for m, (s1, s2) in R32.items():
        W[m] = kw(slots[s1], slots[s2])
        score += W[m] == PICK[m]
    for tab, late in ((R16, False), (QF, True), (SF, True)):
        for m, (m1, m2) in tab.items():
            W[m] = kw(W[m1], W[m2], late)
            score += W[m] == PICK[m]
    score += kw(W[101], W[102], True) == PICK[104]
    X.append([wok[g] for g in "ABCDEFGHIJKL"] + [sok[g] for g in "ABCDEFGHIJKL"])
    y.append(score)

X = np.array(X, dtype=float)
y = np.array(y, dtype=float)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=0)

rf = RandomForestRegressor(n_estimators=300, max_depth=12, min_samples_leaf=20,
                           n_jobs=-1, random_state=0).fit(Xtr, ytr)
bst = xgb.XGBRegressor(n_estimators=400, max_depth=4, learning_rate=0.05,
                       subsample=0.8, colsample_bytree=0.8, random_state=0,
                       n_jobs=-1).fit(Xtr, ytr)
r2_rf, r2_xgb = rf.score(Xte, yte), bst.score(Xte, yte)
print(f"test R^2 -- RandomForest {r2_rf:.3f} | XGBoost {r2_xgb:.3f}")

# SHAP directional importance for XGBoost
expl = shap.TreeExplainer(bst)
sv = expl.shap_values(Xte)
mean_abs = np.abs(sv).mean(axis=0)
# directional: mean SHAP when feature==1 (correct call) minus baseline
order = np.argsort(mean_abs)[::-1]
print("\nXGBoost SHAP importance (mean |SHAP|, points of knockout score):")
rows = []
for i in order[:10]:
    mask = Xte[:, i] == 1
    dir_effect = sv[mask, i].mean() if mask.sum() else 0.0
    print(f"  {feat[i]:<24} |SHAP|={mean_abs[i]:.3f}  effect when correct={dir_effect:+.3f} pts")
    rows.append({"feature": feat[i], "mean_abs_shap": round(float(mean_abs[i]), 4),
                 "effect_when_correct": round(float(dir_effect), 4),
                 "rf_importance": round(float(rf.feature_importances_[i]), 4)})

# rank agreement between RF and XGBoost (Spearman on impurity importances)
from scipy.stats import spearmanr
rho = spearmanr(rf.feature_importances_, bst.feature_importances_).statistic
print(f"\nRF vs XGBoost importance rank correlation (Spearman) = {rho:.3f}")
json.dump({"r2_rf": round(float(r2_rf), 3), "r2_xgb": round(float(r2_xgb), 3),
           "spearman": round(float(rho), 3), "shap": rows},
          open(DATA / "ml_risk_xgb.json", "w"), indent=1)
