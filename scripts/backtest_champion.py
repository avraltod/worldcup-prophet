"""Champion-forecast backtest: simulate the 2018 and 2022 World Cups 50,000
times each from pre-tournament Elo (32-team format), and report where the model
ranked the actual champion, with the market's pre-tournament odds for comparison.
"""
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from poisson_model import fit_rates, pois, MAX_G

DATA = Path(__file__).parent.parent / "data" / "backtest"
N = 50000

GROUPS = {
 2018: {"A": ["Russia", "Saudi Arabia", "Egypt", "Uruguay"],
        "B": ["Portugal", "Spain", "Morocco", "Iran"],
        "C": ["France", "Australia", "Peru", "Denmark"],
        "D": ["Argentina", "Iceland", "Croatia", "Nigeria"],
        "E": ["Brazil", "Switzerland", "Costa Rica", "Serbia"],
        "F": ["Germany", "Mexico", "Sweden", "South Korea"],
        "G": ["Belgium", "Panama", "Tunisia", "England"],
        "H": ["Poland", "Senegal", "Colombia", "Japan"]},
 2022: {"A": ["Qatar", "Ecuador", "Senegal", "Netherlands"],
        "B": ["England", "Iran", "USA", "Wales"],
        "C": ["Argentina", "Saudi Arabia", "Mexico", "Poland"],
        "D": ["France", "Australia", "Denmark", "Tunisia"],
        "E": ["Spain", "Costa Rica", "Germany", "Japan"],
        "F": ["Belgium", "Canada", "Morocco", "Croatia"],
        "G": ["Brazil", "Serbia", "Switzerland", "Cameroon"],
        "H": ["Portugal", "Ghana", "Uruguay", "South Korea"]},
}
HOSTS = {2018: "Russia", 2022: "Qatar"}
CHAMPION = {2018: "France", 2022: "Argentina"}
# standard 32-team R16 wiring (winner/runner-up of groups)
R16 = [("A", "B"), ("C", "D"), ("E", "F"), ("G", "H"),
       ("B", "A"), ("D", "C"), ("F", "E"), ("H", "G")]  # (1st of g1, 2nd of g2)


def elo_hda(ra, rb):
    d = ra - rb
    e = 1.0 / (1.0 + 10 ** (-d / 400.0))
    pd_ = 0.30 * math.exp(-abs(d) / 700.0)
    ph = max(0.01, e - pd_ / 2)
    pa = max(0.01, 1.0 - ph - pd_)
    s = ph + pd_ + pa
    return ph / s, pd_ / s, pa / s


def sample(lam):
    r, acc = random.random(), 0.0
    for k in range(MAX_G + 1):
        acc += pois(k, lam)
        if r <= acc:
            return k
    return MAX_G


def run_year(year):
    elo = json.loads((DATA / f"elo_{year}.json").read_text())
    groups = GROUPS[year]
    host = HOSTS[year]
    R = {t: elo.get(t, elo.get({"USA":"USA"}.get(t,t))) + (40 if t == host else 0) for g in groups.values() for t in g}
    # precompute group-match Poisson rates
    rates = {}
    for g, teams in groups.items():
        for i in range(4):
            for j in range(i + 1, 4):
                a, b = teams[i], teams[j]
                ph, pd_, pa = elo_hda(R[a], R[b])
                rates[(a, b)] = fit_rates(ph, pd_, pa)

    def kowin(a, b):
        ph, pd_, pa = elo_hda(R[a], R[b])
        # collapse draw onto the stronger side (penalties ~ Elo-weighted)
        e = ph + pd_ / 2
        return a if random.random() < e / (ph + pa + pd_) else b

    random.seed(2026)
    champ = Counter()
    for _ in range(N):
        winners, runners = {}, {}
        for g, teams in groups.items():
            st = defaultdict(lambda: [0, 0, 0])
            for i in range(4):
                for j in range(i + 1, 4):
                    a, b = teams[i], teams[j]
                    lh, la = rates[(a, b)]
                    hg, ag = sample(lh), sample(la)
                    for t, f, x in ((a, hg, ag), (b, ag, hg)):
                        st[t][1] += f - x
                        st[t][2] += f
                        st[t][0] += 3 if f > x else (1 if f == x else 0)
            o = sorted(teams, key=lambda t: (*st[t], random.random()), reverse=True)
            winners[g], runners[g] = o[0], o[1]
        # R16
        r16 = []
        for g1, g2 in R16:
            r16.append(kowin(winners[g1], runners[g2]))
        # QF, SF, F
        while len(r16) > 1:
            r16 = [kowin(r16[k], r16[k + 1]) for k in range(0, len(r16), 2)]
        champ[r16[0]] += 1
    return {t: c / N for t, c in champ.most_common()}


if __name__ == "__main__":
    out = {}
    for year in (2018, 2022):
        probs = run_year(year)
        actual = CHAMPION[year]
        rank = [t for t, _ in sorted(probs.items(), key=lambda x: -x[1])].index(actual) + 1
        out[year] = {"probs": probs, "actual": actual, "actual_prob": probs.get(actual, 0),
                     "actual_rank": rank}
        print(f"=== {year}: actual champion {actual} ===")
        print(f"  model gave {actual} a {probs.get(actual,0)*100:.1f}% champion chance, "
              f"ranked #{rank} of 32")
        print("  model's top 6:")
        for t, p in sorted(probs.items(), key=lambda x: -x[1])[:6]:
            star = "  <-- ACTUAL CHAMPION" if t == actual else ""
            print(f"    {t:<14} {p*100:5.1f}%{star}")
        print()
    (DATA / "champion_backtest.json").write_text(json.dumps(out, indent=1))
    print("saved data/backtest/champion_backtest.json")
