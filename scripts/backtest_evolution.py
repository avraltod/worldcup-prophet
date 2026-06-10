"""Forecast evolution on real tournaments: replay 2018 and 2022 match by match,
conditioning on actual results, to show how the champion forecast moved and how
much information each result carried. Tests the live study's three hypotheses on
real data. Two teams in the same group => group match; otherwise => knockout."""
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from poisson_model import fit_rates, pois, MAX_G
from backtest_champion import GROUPS, HOSTS, CHAMPION, R16, elo_hda, sample

DATA = Path(__file__).parent.parent / "data" / "backtest"
N = 12000
ALIAS = {"United States": "USA"}

# actual group winners (1st) and runners-up (2nd) -- historical fact
ACTUAL_QUAL = {
 2018: {"A": ("Uruguay", "Russia"), "B": ("Spain", "Portugal"),
        "C": ("France", "Denmark"), "D": ("Croatia", "Argentina"),
        "E": ("Brazil", "Switzerland"), "F": ("Sweden", "Mexico"),
        "G": ("Belgium", "England"), "H": ("Colombia", "Japan")},
 2022: {"A": ("Netherlands", "Senegal"), "B": ("England", "USA"),
        "C": ("Argentina", "Poland"), "D": ("France", "Australia"),
        "E": ("Japan", "Spain"), "F": ("Morocco", "Croatia"),
        "G": ("Brazil", "Switzerland"), "H": ("Portugal", "South Korea")},
}


def run(year):
    elo = json.loads((DATA / f"elo_{year}.json").read_text())
    results = json.loads((DATA / f"results_{year}.json").read_text())
    groups = GROUPS[year]
    host = HOSTS[year]
    R = {t: elo.get(t, elo.get(ALIAS.get(t, t))) + (40 if t == host else 0)
         for g in groups.values() for t in g}
    team_group = {t: g for g, ts in groups.items() for t in ts}

    def norm(t):
        return t if t in R else ALIAS.get(t, t)

    # precompute group-fixture rates
    rates = {}
    for g, ts in groups.items():
        for i in range(4):
            for j in range(i + 1, 4):
                a, b = ts[i], ts[j]
                rates[frozenset((a, b))] = fit_rates(*elo_hda(R[a], R[b]))

    def kowin(a, b):
        ph, pd_, pa = elo_hda(R[a], R[b])
        e = ph + pd_ / 2
        return a if random.random() < e else b

    aqual = ACTUAL_QUAL[year]

    def conditional(pg, pko):
        random.seed(2026)
        champ = Counter()
        for _ in range(N):
            winners, runners = {}, {}
            for g, ts in groups.items():
                # if all six group fixtures are observed, use the actual qualifiers
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
            r16 = [(winners[g1], runners[g2]) for g1, g2 in R16]
            teams = []
            for a, b in r16:
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
            s.add(norm(mm["home"]))
            s.add(norm(mm["away"]))
        return s

    pg, pko = {}, {}
    base = conditional(pg, pko)
    traj = [{"n": 0, "champion": {t: round(v, 4) for t, v in base.items()},
             "info_bits": 0.0, "label": "baseline"}]
    prev = base
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
                # penalty/extra-time draw: advancer is the team that plays again
                lt = later_teams(idx)
                win = h if h in lt else (a if a in lt else champion)
            pko[frozenset((h, a))] = win
        cur = conditional(pg, pko)
        traj.append({"n": idx, "champion": {t: round(v, 4) for t, v in cur.items()},
                     "info_bits": round(kl(cur, prev), 4), "kind": kind,
                     "label": f"{m['home']} {m['hg']}-{m['ag']} {m['away']}"})
        prev = cur
    return traj


if __name__ == "__main__":
    for year in (2018, 2022):
        traj = run(year)
        (DATA / f"evolution_{year}.json").write_text(json.dumps(traj, ensure_ascii=False, indent=1))
        actual = CHAMPION[year]
        ch = [e["champion"].get(actual, 0) * 100 for e in traj]
        infos = [(e["n"], e["info_bits"], e["kind"], e["label"]) for e in traj[1:]]
        total = sum(b for _, b, _, _ in infos)
        gi = sum(b for _, b, k, _ in infos if k == "group")
        top = sorted(infos, key=lambda x: -x[1])[:4]
        print(f"=== {year}: {actual} champion probability {ch[0]:.0f}% -> {ch[-1]:.0f}% ===")
        print(f"  total information {total:.2f} bits | group stage {100*gi/total:.0f}% vs knockouts {100*(total-gi)/total:.0f}%")
        print(f"  most informative results:")
        for n, b, k, lab in top:
            print(f"    match {n} ({b:.2f} bits): {lab}")
        print()
