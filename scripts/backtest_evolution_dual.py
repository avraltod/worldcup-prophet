"""A4: forecast-evolution under frozen-strength vs strength-updating models.

The live study freezes pre-tournament strengths and conditions only on bracket
structure. A referee objection is that this mechanically suppresses group-stage
information, because a dominant group win that should raise a team's strength is
scored near zero. This script re-runs the 2018/2022 evolution with Elo strengths
UPDATED after each result (standard Elo, goal-difference multiplier, K=40) and
compares the information trajectory to the frozen version, to test whether the
conclusion -- information concentrates in the knockouts -- survives updating.
"""
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from poisson_model import fit_rates
from backtest_champion import GROUPS, HOSTS, CHAMPION, R16, elo_hda, sample
from backtest_evolution import ACTUAL_QUAL

DATA = Path(__file__).parent.parent / "data" / "backtest"
N = 6000
ALIAS = {"United States": "USA"}
K = 40


def gd_mult(gd):
    g = abs(gd)
    return 1.0 if g <= 1 else (1.5 if g == 2 else (11 + g) / 8)


def run(year, update):
    elo = json.loads((DATA / f"elo_{year}.json").read_text())
    results = json.loads((DATA / f"results_{year}.json").read_text())
    groups = GROUPS[year]
    host = HOSTS[year]
    R = {t: elo.get(t, elo.get(ALIAS.get(t, t))) + (40 if t == host else 0)
         for g in groups.values() for t in g}
    team_group = {t: g for g, ts in groups.items() for t in ts}
    aqual = ACTUAL_QUAL[year]

    def norm(t):
        return t if t in R else ALIAS.get(t, t)

    def build_rates():
        r = {}
        for g, ts in groups.items():
            for i in range(4):
                for j in range(i + 1, 4):
                    a, b = ts[i], ts[j]
                    r[frozenset((a, b))] = fit_rates(*elo_hda(R[a], R[b]))
        return r

    rates = build_rates()

    def kowin(a, b):
        ph, pd_, pa = elo_hda(R[a], R[b])
        return a if random.random() < ph + pd_ / 2 else b

    def conditional(pg, pko):
        random.seed(2026)
        champ = Counter()
        for _ in range(N):
            winners, runners = {}, {}
            for g, ts in groups.items():
                complete = all(frozenset((ts[i], ts[j])) in pg
                               for i in range(4) for j in range(i + 1, 4))
                if complete:
                    winners[g], runners[g] = aqual[g]
                    continue
                st = defaultdict(lambda: [0, 0, 0])
                for i in range(4):
                    for j in range(i + 1, 4):
                        a, b = ts[i], ts[j]
                        key = frozenset((a, b))
                        if key in pg:
                            hg, ag, ha = pg[key]
                            sa, sb = (hg, ag) if ha == a else (ag, hg)
                        else:
                            lh, la = rates[key]
                            sa, sb = sample(lh), sample(la)
                        for t, f, x in ((a, sa, sb), (b, sb, sa)):
                            st[t][1] += f - x
                            st[t][2] += f
                            st[t][0] += 3 if f > x else (1 if f == x else 0)
                o = sorted(ts, key=lambda t: (*st[t], random.random()), reverse=True)
                winners[g], runners[g] = o[0], o[1]
            teams = []
            for a, b in [(winners[g1], runners[g2]) for g1, g2 in R16]:
                key = frozenset((a, b))
                teams.append(pko[key] if key in pko else kowin(a, b))
            while len(teams) > 1:
                nxt = []
                for k in range(0, len(teams), 2):
                    a, b = teams[k], teams[k + 1]
                    key = frozenset((a, b))
                    nxt.append(pko[key] if key in pko else kowin(a, b))
                teams = nxt
            champ[teams[0]] += 1
        return {t: c / N for t, c in champ.items()}

    def kl(q, p):
        eps = 1e-6
        return sum((q.get(t, 0) + eps) * math.log2((q.get(t, 0) + eps) / (p.get(t, 0) + eps))
                   for t in set(q) | set(p))

    champion = CHAMPION[year]

    def later_teams(p):
        s = set()
        for mm in results[p:]:
            s.add(norm(mm["home"])); s.add(norm(mm["away"]))
        return s

    def elo_update(a, b, ga, gb):
        ea = 1 / (1 + 10 ** (-(R[a] - R[b]) / 400))
        sa = 1.0 if ga > gb else (0.5 if ga == gb else 0.0)
        d = K * gd_mult(ga - gb) * (sa - ea)
        R[a] += d; R[b] -= d

    pg, pko = {}, {}
    prev = conditional(pg, pko)
    infos = []
    for idx, m in enumerate(results, 1):
        h, a = norm(m["home"]), norm(m["away"])
        if h in team_group and a in team_group and team_group[h] == team_group[a]:
            pg[frozenset((h, a))] = (m["hg"], m["ag"], h)
            kind = "group"
        else:
            kind = "ko"
            if m["hg"] > m["ag"]:
                win = h
            elif m["ag"] > m["hg"]:
                win = a
            else:
                lt = later_teams(idx)
                win = h if h in lt else (a if a in lt else champion)
            pko[frozenset((h, a))] = win
        if update:
            elo_update(h, a, m["hg"], m["ag"])
            rates = build_rates()
        cur = conditional(pg, pko)
        infos.append((kind, kl(cur, prev)))
        prev = cur
    total = sum(b for _, b in infos)
    gi = sum(b for k, b in infos if k == "group")
    return total, gi


if __name__ == "__main__":
    print("=== A4: information trajectory, frozen vs strength-updating ===\n")
    for year in (2018, 2022):
        tf, gf = run(year, update=False)
        tu, gu = run(year, update=True)
        print(f"{year}:")
        print(f"  FROZEN strengths:   total {tf:.2f} bits | group-stage share {100*gf/tf:.0f}% | knockouts {100*(tf-gf)/tf:.0f}%")
        print(f"  UPDATING strengths: total {tu:.2f} bits | group-stage share {100*gu/tu:.0f}% | knockouts {100*(tu-gu)/tu:.0f}%")
        print()
