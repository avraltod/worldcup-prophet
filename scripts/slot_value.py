"""B2: the value of slot-emergence across the whole bracket and across brackets.

Slot emergence picks, for each knockout match, the team maximizing P(reaches and
wins the slot) rather than the strongest team or the most likely occupant. This
quantifies its aggregate value over all 31 knockout matches, and repeats the
comparison on several strength-perturbed tournaments so the result is not a
property of one bracket. Reports expected knockout points (3-2-1 collapses to the
slot-emergence objective here, since a knockout pick scores when its team occupies
and wins the slot) for three entries: slot-emergence, modal-occupant, strongest.
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
ELO0 = {t["team"]: t["elo"] for t in info["elo"]}
ADJ = dict(info["injury_elo_adj"])
ADJ["Portugal"] = ADJ.get("Portugal", 0) + 66
ADJ["Colombia"] = ADJ.get("Colombia", 0) - 67
HOSTS = {"Mexico": 40, "United States": 40, "Canada": 40}
preds = json.loads((DATA / "group_predictions.json").read_text())
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


def simulate(elo, match_rates):
    def rating(team, late=False):
        r = elo[team] + ADJ.get(team, 0)
        return r + ((20 if late else 40) if team in HOSTS else 0)
    def kowin(a, b, late=False):
        e = 1 / (1 + 10 ** (-(rating(a, late) - rating(b, late)) / 400))
        return a if random.random() < e else b
    slotw = defaultdict(Counter)   # who wins match m
    reach = defaultdict(Counter)   # who reaches match m
    for _ in range(N):
        pos, thirds = {}, {}
        for grp in "ABCDEFGHIJKL":
            stats = defaultdict(lambda: [0, 0, 0])
            for row in GROUPS[grp]:
                lh, la, home, away = match_rates[row]
                hg, ag = sample(lh), sample(la)
                for t, f, g in ((home, hg, ag), (away, ag, hg)):
                    stats[t][1] += f - g; stats[t][2] += f
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
            reach[m][slots[s1]] += 1; reach[m][slots[s2]] += 1
            W[m] = kowin(slots[s1], slots[s2]); slotw[m][W[m]] += 1
        for tab, late in ((R16, False), (QF, True), (SF, True)):
            for m, (m1, m2) in tab.items():
                reach[m][W[m1]] += 1; reach[m][W[m2]] += 1
                W[m] = kowin(W[m1], W[m2], late); slotw[m][W[m]] += 1
        reach[104][W[101]] += 1; reach[104][W[102]] += 1
        slotw[104][kowin(W[101], W[102], True)] += 1
    return slotw, reach, rating


def entries(slotw, reach, rating):
    ko = list(R32) + list(R16) + list(QF) + list(SF) + [104]
    se = mo = st = 0.0
    for m in ko:
        if not slotw[m]:
            continue
        se += max(slotw[m].values()) / N                       # slot-emergence
        modal = reach[m].most_common(1)[0][0]
        mo += slotw[m][modal] / N                              # modal occupant
        strongest = max(reach[m], key=lambda t: rating(t))
        st += slotw[m][strongest] / N                          # strongest reachable
    return se, mo, st


def main():
    base_rates = {}
    for p in preds:
        ph, pd, pa = p["p"]; s = ph + pd + pa
        base_rates[p["row"]] = (*fit_rates(ph / s, pd / s, pa / s), p["home"], p["away"])
    print("=== B2: slot-emergence value across the whole bracket and across brackets ===")
    print("Expected knockout points (sum over 31 KO matches); higher is better.\n")
    print("  bracket          | slot-emergence | modal-occupant | strongest")
    for trial in range(5):
        if trial == 0:
            elo = dict(ELO0); rates = base_rates; tag = "actual 2026"
        else:
            random.seed(100 + trial)
            elo = {t: v + random.gauss(0, 80) for t, v in ELO0.items()}
            # rebuild group rates from perturbed Elo via Elo-implied 1x2
            rates = {}
            for p in preds:
                a, b = p["home"], p["away"]
                d = (elo.get(a, 1500) + ADJ.get(a, 0)) - (elo.get(b, 1500) + ADJ.get(b, 0))
                e = 1 / (1 + 10 ** (-d / 400)); pdr = 0.27
                ph = max(.05, e - pdr / 2); pa = max(.05, 1 - ph - pdr); s = ph + pdr + pa
                rates[p["row"]] = (*fit_rates(ph / s, pdr / s, pa / s), a, b)
            tag = f"perturbed #{trial}"
        random.seed(2026)
        sw, rc, rt = simulate(elo, rates)
        se, mo, st = entries(sw, rc, rt)
        print(f"  {tag:16s} |     {se:5.2f}      |     {mo:5.2f}      |   {st:5.2f}  "
              f"  (SE beats strongest by {se-st:+.2f}, modal by {se-mo:+.2f})")


if __name__ == "__main__":
    main()
