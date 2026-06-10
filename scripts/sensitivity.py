"""Reviewer fix: one-at-a-time sensitivity sweep over the hand-set constants.

Varies (a) injury-adjustment scale {0, 0.5, 1, 1.5, 2}, (b) host bonus
{0, 20, 40, 60}, (c) draw-model base {0.22, 0.30, 0.38} and scale {500, 900}.
For each config, re-runs the tournament simulation (20k) and reports:
  - sign/size of the three contested slot-emergence gaps
    (Norway-Ecuador M78, Croatia-Portugal M83, Belgium-Turkey M94)
  - champion and champion probability
Note: the draw-model constants affect knockout advancement via ko_winner's
underlying expectancy only through ratings here (draws are folded into the
Bernoulli), so draw params are exercised via the group-stage Poisson tier
indirectly; the binding test for the flips is (a) + (b).
"""
import json
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
BASE_ADJ = info["injury_elo_adj"]

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


def run(adj_scale=1.0, host=40, host_late=20):
    random.seed(2026)
    hostmap = {"Mexico": host, "United States": host, "Canada": host}
    hostmap_late = {k: host_late for k in hostmap}

    def rating(team, late=False):
        r = ELO[team] + adj_scale * BASE_ADJ.get(team, 0)
        hm = hostmap_late if late else hostmap
        return r + hm.get(team, 0)

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

    g78 = (slotw[78]["Norway"] - slotw[78]["Ecuador"]) / N * 100
    g83 = (slotw[83]["Croatia"] - slotw[83]["Portugal"]) / N * 100
    g94 = (slotw[94]["Belgium"] - slotw[94]["Turkey"]) / N * 100
    c, cn = champ.most_common(1)[0]
    return g78, g83, g94, c, cn / N * 100


print(f"{'config':<28} {'NOR-ECU':>8} {'CRO-POR':>8} {'BEL-TUR':>8}  champion")
for label, kw in [
    ("baseline", {}),
    ("injuries off (x0)", {"adj_scale": 0}),
    ("injuries x0.5", {"adj_scale": 0.5}),
    ("injuries x1.5", {"adj_scale": 1.5}),
    ("injuries x2", {"adj_scale": 2}),
    ("host 0/0", {"host": 0, "host_late": 0}),
    ("host 20/10", {"host": 20, "host_late": 10}),
    ("host 60/30", {"host": 60, "host_late": 30}),
]:
    g78, g83, g94, c, cp = run(**kw)
    print(f"{label:<28} {g78:>+7.1f}pp {g83:>+7.1f}pp {g94:>+7.1f}pp  {c} {cp:.1f}%")
