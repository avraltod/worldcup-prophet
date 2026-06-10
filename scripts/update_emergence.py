"""Post-refresh slot-emergence check: re-simulate with updated group K rates
(Portugal Elo also raised by the market-implied margin for knockouts) and
report emergence for the affected slots."""
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import GROUP_FIXTURES
from poisson_model import fit_rates, pois, MAX_G

DATA = Path(__file__).parent.parent / "data"
N = 50000

info = json.loads((DATA / "elo_outright_news.json").read_text())
ELO = {t["team"]: t["elo"] for t in info["elo"]}
ADJ = dict(info["injury_elo_adj"])
# market-implied recalibration: split the 140-pt implied gap around the raw
# 7-pt Elo difference -> Portugal +66, Colombia -67 relative to raw ratings
ADJ["Portugal"] = ADJ.get("Portugal", 0) + 66
ADJ["Colombia"] = ADJ.get("Colombia", 0) - 67
HOSTS = {"Mexico": 40, "United States": 40, "Canada": 40}

preds = json.loads((DATA / "group_predictions.json").read_text())
MATCH_RATES = {}
for p in preds:
    ph, pd, pa = p["p"]
    s = ph + pd + pa
    MATCH_RATES[p["row"]] = (*fit_rates(ph / s, pd / s, pa / s), p["home"], p["away"])
GROUPS = defaultdict(list)
for row, grp, h, a in GROUP_FIXTURES:
    GROUPS[grp].append(row)

THIRD_SLOTS = {74: set("ABCDF"), 77: set("CDFGH"), 81: set("BEFIJ"),
               82: set("AEHIJ"), 79: set("CEFHI"), 80: set("EHIJK"),
               85: set("EFGIJ"), 87: set("DEIJL")}
SLOT_ORDER = list(THIRD_SLOTS)
R32 = {74: ("E1", "T74"), 77: ("I1", "T77"), 73: ("A2", "B2"), 75: ("F1", "C2"),
       76: ("C1", "F2"), 78: ("E2", "I2"), 79: ("A1", "T79"), 80: ("L1", "T80"),
       83: ("K2", "L2"), 84: ("H1", "J2"), 81: ("D1", "T81"), 82: ("G1", "T82"),
       86: ("J1", "H2"), 88: ("D2", "G2"), 85: ("B1", "T85"), 87: ("K1", "T87")}
R16 = {89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
       93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87)}
QF = {97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96)}
SF = {101: (97, 98), 102: (99, 100)}

random.seed(2026)


def rating(team, late=False):
    hm = 20 if late else 40
    r = ELO[team] + ADJ.get(team, 0)
    return r + (hm if team in HOSTS else 0)


def kowin(a, b, late=False):
    e = 1 / (1 + 10 ** (-(rating(a, late) - rating(b, late)) / 400))
    return a if random.random() < e else b


def sample(lam):
    r, acc = random.random(), 0.0
    for k in range(MAX_G + 1):
        acc += pois(k, lam)
        if r <= acc:
            return k
    return MAX_G


def assign(qualified):
    def bt(i, used):
        if i == len(SLOT_ORDER):
            return {}
        cands = [g for g in qualified if g not in used and g in THIRD_SLOTS[SLOT_ORDER[i]]]
        random.shuffle(cands)
        for g in cands:
            rest = bt(i + 1, used | {g})
            if rest is not None:
                rest[SLOT_ORDER[i]] = g
                return rest
        return None
    return bt(0, set())


slotw = defaultdict(Counter)
champ = Counter()
k1 = Counter()
for _ in range(N):
    pos, thirds = {}, {}
    for grp in "ABCDEFGHIJKL":
        stats = defaultdict(lambda: [0, 0, 0])
        for row in GROUPS[grp]:
            lh, la, home, away = MATCH_RATES[row]
            hg, ag = sample(lh), sample(la)
            for t, f, g in ((home, hg, ag), (away, ag, hg)):
                stats[t][1] += f - g
                stats[t][2] += f
                stats[t][0] += 3 if f > g else (1 if f == g else 0)
        order = sorted(stats, key=lambda t: (*stats[t], random.random()), reverse=True)
        pos[f"{grp}1"], pos[f"{grp}2"] = order[0], order[1]
        thirds[grp] = (order[2], tuple(stats[order[2]]))
    k1[pos["K1"]] += 1
    ranked = sorted(thirds, key=lambda g: (*thirds[g][1], random.random()), reverse=True)
    am = assign(ranked[:8]) or assign(ranked[:7] + [ranked[8]])
    if am is None:
        continue
    slots = dict(pos)
    for m, g in am.items():
        slots[f"T{m}"] = thirds[g][0]
    W = {}
    for m, (s1, s2) in R32.items():
        W[m] = kowin(slots[s1], slots[s2])
        slotw[m][W[m]] += 1
    for tab, late in ((R16, False), (QF, True), (SF, True)):
        for m, (m1, m2) in tab.items():
            W[m] = kowin(W[m1], W[m2], late)
            slotw[m][W[m]] += 1
    champ[kowin(W[101], W[102], True)] += 1

print(f"=== post-refresh simulation, N={N} ===")
print("Group K winner:", {t: round(c / N, 3) for t, c in k1.most_common(4)})
for m in (87, 83, 96, 100, 78, 94):
    top = ", ".join(f"{t} {100 * c / N:.1f}%" for t, c in slotw[m].most_common(3))
    print(f"slot M{m}: {top}")
print("champion:", ", ".join(f"{t} {100 * c / N:.1f}%" for t, c in champ.most_common(5)))
