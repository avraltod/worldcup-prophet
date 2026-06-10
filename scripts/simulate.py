"""Monte Carlo simulation of the full 2026 World Cup.

Group stage: sample exact scores from per-match Poisson rates fitted to the
odds-implied probabilities (same fits used for the sheet predictions).
Standings: Pts, GD, GF, head-to-head, then random. Best 8 third-placed teams
(Pts, GD, GF, random) assigned to R32 slots by bipartite matching against the
template's slot constraints. Knockouts: Elo + injury adj + host bonus; draws
resolved by Elo-weighted shootout.

Outputs champion/final-four probabilities and, for the current sheet bracket,
how often each predicted matchup and advancer materializes.
"""
import json
import random
import sys
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import GROUP_FIXTURES
from poisson_model import fit_rates, pois, MAX_G

DATA = Path(__file__).parent.parent / "data"
N_SIMS = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
random.seed(2026)

info = json.loads((DATA / "elo_outright_news.json").read_text())
ELO = {t["team"]: t["elo"] for t in info["elo"]}
ADJ = info["injury_elo_adj"]
HOSTS = {"Mexico": 40, "United States": 40, "Canada": 40}

# ---- group stage machinery -------------------------------------------------
preds = json.loads((DATA / "group_predictions.json").read_text())
MATCH_RATES = {}   # row -> (lh, la, home, away, group)
for p in preds:
    ph, pd, pa = p["p"]
    s = ph + pd + pa
    MATCH_RATES[p["row"]] = (*fit_rates(ph / s, pd / s, pa / s),
                             p["home"], p["away"], p["group"])

GROUPS = defaultdict(list)
for row, grp, h, a in GROUP_FIXTURES:
    GROUPS[grp].append(row)


def sample_score(lh, la):
    def draw(lam):
        r, acc = random.random(), 0.0
        for k in range(MAX_G + 1):
            acc += pois(k, lam)
            if r <= acc:
                return k
        return MAX_G
    return draw(lh), draw(la)


def simulate_group(grp):
    """Returns ordered team list [1st, 2nd, 3rd, 4th] + stats of the 3rd."""
    stats = defaultdict(lambda: [0, 0, 0])  # pts, gd, gf
    h2h = {}
    for row in GROUPS[grp]:
        lh, la, home, away, _ = MATCH_RATES[row]
        hg, ag = sample_score(lh, la)
        for t, f, g in ((home, hg, ag), (away, ag, hg)):
            stats[t][1] += f - g
            stats[t][2] += f
            stats[t][0] += 3 if f > g else (1 if f == g else 0)
        h2h[(home, away)] = (hg, ag)

    def key(t):
        return (stats[t][0], stats[t][1], stats[t][2], random.random())
    order = sorted(stats, key=key, reverse=True)
    # head-to-head check only for exact pts/gd/gf two-way ties (cheap approx)
    for i in range(3):
        a, b = order[i], order[i + 1]
        if stats[a][:3] == stats[b][:3]:
            r = h2h.get((a, b)) or tuple(reversed(h2h.get((b, a), (0, 0))))
            if r and r[1] > r[0]:
                order[i], order[i + 1] = b, a
    third = order[2]
    return order, (stats[third][0], stats[third][1], stats[third][2])


# ---- 3rd-place allocation (template slot constraints) ----------------------
THIRD_SLOTS = {  # match number -> allowed 3rd-place groups
    74: set("ABCDF"), 77: set("CDFGH"), 81: set("BEFIJ"), 82: set("AEHIJ"),
    79: set("CEFHI"), 80: set("EHIJK"), 85: set("EFGIJ"), 87: set("DEIJL"),
}
SLOT_ORDER = list(THIRD_SLOTS)


def assign_thirds(qualified):  # qualified: list of 8 group letters
    """Bipartite matching qualified groups -> slots; returns dict slot->group."""
    def backtrack(i, used):
        if i == len(SLOT_ORDER):
            return {}
        slot = SLOT_ORDER[i]
        cands = [g for g in qualified if g not in used and g in THIRD_SLOTS[slot]]
        random.shuffle(cands)
        for g in cands:
            rest = backtrack(i + 1, used | {g})
            if rest is not None:
                rest[slot] = g
                return rest
        return None
    return backtrack(0, set())


# ---- knockout machinery -----------------------------------------------------
def ko_rating(team, late=False):
    r = ELO[team] + ADJ.get(team, 0)
    if team in HOSTS:
        r += HOSTS[team] if not late else 20
    return r


def ko_winner(a, b, late=False):
    ra, rb = ko_rating(a, late), ko_rating(b, late)
    e = 1.0 / (1.0 + 10 ** (-(ra - rb) / 400.0))
    return a if random.random() < e else b


# Bracket wiring: R32 match -> (home slot, away slot); slots like "A1","B2","T74"=3rd in match 74
R32 = {74: ("E1", "T74"), 77: ("I1", "T77"), 73: ("A2", "B2"), 75: ("F1", "C2"),
       76: ("C1", "F2"), 78: ("E2", "I2"), 79: ("A1", "T79"), 80: ("L1", "T80"),
       83: ("K2", "L2"), 84: ("H1", "J2"), 81: ("D1", "T81"), 82: ("G1", "T82"),
       86: ("J1", "H2"), 88: ("D2", "G2"), 85: ("B1", "T85"), 87: ("K1", "T87")}
R16 = {89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
       93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87)}
QF = {97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96)}
SF = {101: (97, 98), 102: (99, 100)}

# Sheet's predicted bracket (for materialization stats)
SHEET = {
    "R32": {74: ("Germany", "Paraguay", "Germany"), 77: ("France", "Sweden", "France"),
            73: ("South Korea", "Canada", "Canada"), 75: ("Netherlands", "Morocco", "Netherlands"),
            83: ("Portugal", "Croatia", "Portugal"), 84: ("Spain", "Austria", "Spain"),
            81: ("Turkey", "Bosnia and Herzegovina", "Turkey"), 82: ("Belgium", "Czechia", "Belgium"),
            76: ("Brazil", "Japan", "Brazil"), 78: ("Ecuador", "Norway", "Ecuador"),
            79: ("Mexico", "Ivory Coast", "Mexico"), 80: ("England", "Algeria", "England"),
            86: ("Argentina", "Uruguay", "Argentina"), 88: ("United States", "Egypt", "United States"),
            85: ("Switzerland", "Iran", "Switzerland"), 87: ("Colombia", "Senegal", "Colombia")},
    "R16": {89: ("Germany", "France", "France"), 90: ("Canada", "Netherlands", "Netherlands"),
            93: ("Portugal", "Spain", "Spain"), 94: ("Turkey", "Belgium", "Turkey"),
            91: ("Brazil", "Ecuador", "Brazil"), 92: ("Mexico", "England", "England"),
            95: ("Argentina", "United States", "Argentina"), 96: ("Switzerland", "Colombia", "Colombia")},
    "QF": {97: ("France", "Netherlands", "France"), 98: ("Spain", "Turkey", "Spain"),
           99: ("Brazil", "England", "England"), 100: ("Argentina", "Colombia", "Argentina")},
    "SF": {101: ("France", "Spain", "Spain"), 102: ("England", "Argentina", "Argentina")},
    "Final": {104: ("Spain", "Argentina", "Spain")},
}

champ = Counter()
finalist = Counter()
semis = Counter()
matchup_hits = defaultdict(int)   # (round, match) -> matchup materialized
advance_hits = defaultdict(int)   # (round, match) -> predicted advancer advanced
reach = defaultdict(int)          # (round, match, team) -> team appeared in that match

for _ in range(N_SIMS):
    pos = {}
    thirds = {}
    for grp in "ABCDEFGHIJKL":
        order, tstats = simulate_group(grp)
        pos[f"{grp}1"], pos[f"{grp}2"] = order[0], order[1]
        thirds[grp] = (order[2], tstats)
    ranked = sorted(thirds, key=lambda g: (*thirds[g][1], random.random()), reverse=True)
    qualified = ranked[:8]
    assign = assign_thirds(qualified)
    if assign is None:  # rare infeasible combo -> swap 8th for 9th
        qualified = ranked[:7] + [ranked[8]]
        assign = assign_thirds(qualified)
        if assign is None:
            continue
    slots = dict(pos)
    for m, g in assign.items():
        slots[f"T{m}"] = thirds[g][0]

    winners = {}
    for m, (s1, s2) in R32.items():
        a, b = slots[s1], slots[s2]
        w = ko_winner(a, b)
        winners[m] = w
        ph, pa, padv = SHEET["R32"][m]
        if {a, b} == {ph, pa}:
            matchup_hits[("R32", m)] += 1
        if w == padv:
            advance_hits[("R32", m)] += 1
    for rnd, table in (("R16", R16), ("QF", QF), ("SF", SF)):
        late = rnd in ("QF", "SF")
        for m, (m1, m2) in table.items():
            a, b = winners[m1], winners[m2]
            w = ko_winner(a, b, late)
            winners[m] = w
            ph, pa, padv = SHEET[rnd][m]
            if {a, b} == {ph, pa}:
                matchup_hits[(rnd, m)] += 1
            if w == padv:
                advance_hits[(rnd, m)] += 1
    f1, f2 = winners[101], winners[102]
    semis[winners[97]] += 1; semis[winners[98]] += 1
    semis[winners[99]] += 1; semis[winners[100]] += 1
    finalist[f1] += 1; finalist[f2] += 1
    if {f1, f2} == {"Spain", "Argentina"}:
        matchup_hits[("Final", 104)] += 1
    w = ko_winner(f1, f2, late=True)
    champ[w] += 1
    if w == "Spain":
        advance_hits[("Final", 104)] += 1

pct = lambda c: f"{100.0 * c / N_SIMS:5.1f}%"
print(f"=== {N_SIMS} simulations ===")
print("\n-- P(champion) top 12 --")
for t, c in champ.most_common(12):
    print(f"  {t:<16} {pct(c)}")
print("\n-- P(reach final) top 8 --")
for t, c in finalist.most_common(8):
    print(f"  {t:<16} {pct(c)}")
print("\n-- P(reach semi-final) top 10 --")
for t, c in semis.most_common(10):
    print(f"  {t:<16} {pct(c)}")
print("\n-- Sheet bracket reality-check (matchup happens / your advancer advances) --")
for rnd in ("R32", "R16", "QF", "SF", "Final"):
    for m, (ph, pa, padv) in SHEET[rnd].items():
        mh = matchup_hits[(rnd, m)]
        ah = advance_hits[(rnd, m)]
        print(f"  {rnd:<5} M{m}: {ph} vs {pa:<22} matchup {pct(mh)} | {padv:<14} advances {pct(ah)}")

# Per-slot emergence: which team most often wins each bracket slot?
# (re-run sims tracking winners per match slot)
random.seed(2026)
slot_win = defaultdict(Counter)
for _ in range(N_SIMS):
    pos = {}
    thirds = {}
    for grp in "ABCDEFGHIJKL":
        order, tstats = simulate_group(grp)
        pos[f"{grp}1"], pos[f"{grp}2"] = order[0], order[1]
        thirds[grp] = (order[2], tstats)
    ranked = sorted(thirds, key=lambda g: (*thirds[g][1], random.random()), reverse=True)
    qualified = ranked[:8]
    assign = assign_thirds(qualified)
    if assign is None:
        qualified = ranked[:7] + [ranked[8]]
        assign = assign_thirds(qualified)
        if assign is None:
            continue
    slots = dict(pos)
    for m, g in assign.items():
        slots[f"T{m}"] = thirds[g][0]
    winners = {}
    for m, (s1, s2) in R32.items():
        winners[m] = ko_winner(slots[s1], slots[s2])
        slot_win[("R32", m)][winners[m]] += 1
    for rnd, table in (("R16", R16), ("QF", QF), ("SF", SF)):
        late = rnd in ("QF", "SF")
        for m, (m1, m2) in table.items():
            winners[m] = ko_winner(winners[m1], winners[m2], late)
            slot_win[(rnd, m)][winners[m]] += 1

print("\n-- Slot emergence: sheet pick vs sheet opponent vs overall best --")
for rnd in ("R32", "R16", "QF", "SF"):
    for m, (ph, pa, padv) in SHEET[rnd].items():
        opp = pa if padv == ph else ph
        c = slot_win[(rnd, m)]
        top2 = ", ".join(f"{t} {100*n/N_SIMS:.1f}%" for t, n in c.most_common(2))
        flag = " <-- FLIP?" if c[opp] > c[padv] else ""
        print(f"  {rnd:<4} M{m}: pick {padv} {100*c[padv]/N_SIMS:.1f}% vs opp {opp} "
              f"{100*c[opp]/N_SIMS:.1f}% | top: {top2}{flag}")
