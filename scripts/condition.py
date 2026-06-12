"""Conditional re-simulation engine: the forecast as it updates on results.

The pre-tournament 200k simulation is the baseline (prior at t=0). After each
match, we FIX the played results and re-simulate only the remaining matches,
keeping every still-alive team's pre-tournament strength (conditioning-only, no
in-tournament strength learning). The output is each team's updated probability
of reaching each stage.

results_log.json format:
  {"group": {"<match_no>": [hg, ag], ...},      # official match numbers 1-72
   "ko":    {"<match_no>": "<winning team>", ...}}  # knockout matches 73-104

Usage (compute a snapshot given the current results log):
  python3 scripts/condition.py [N]   -> writes data/snapshot.json
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

ROW_MATCH = dict(zip(range(4, 76), [
    1, 2, 25, 28, 53, 54,   3, 8, 26, 27, 51, 52,   7, 5, 30, 29, 49, 50,
    4, 6, 31, 32, 59, 60,  10, 9, 34, 33, 56, 55,  11, 12, 36, 35, 58, 57,
    16, 15, 40, 39, 64, 63, 14, 13, 37, 38, 66, 65, 17, 18, 41, 42, 61, 62,
    19, 20, 44, 43, 69, 70, 23, 24, 48, 47, 71, 72, 22, 21, 46, 45, 67, 68]))
MATCH_ROW = {m: r for r, m in ROW_MATCH.items()}

info = json.loads((DATA / "elo_outright_news.json").read_text())
ELO = {t["team"]: t["elo"] for t in info["elo"]}
ADJ = dict(info["injury_elo_adj"])
# Group-K recalibration to prediction-market prices (7 June; see paper Postscript,
# sec:postscript): markets implied a ~140-pt Portugal-Colombia gap vs the Elo near-tie.
ADJ["Portugal"] = ADJ.get("Portugal", 0) + 66
ADJ["Colombia"] = ADJ.get("Colombia", 0) - 67
HOSTS = {"Mexico", "United States", "Canada"}

preds = json.loads((DATA / "group_predictions.json").read_text())
RATES = {}
for p in preds:
    ph, pd, pa = p["p"]
    s = ph + pd + pa
    RATES[p["row"]] = (*fit_rates(ph / s, pd / s, pa / s), p["home"], p["away"])
GROUPS = defaultdict(list)
for row, grp, h, a in GROUP_FIXTURES:
    GROUPS[grp].append(row)

TS = {74: set("ABCDF"), 77: set("CDFGH"), 81: set("BEFIJ"), 82: set("AEHIJ"),
      79: set("CEFHI"), 80: set("EHIJK"), 85: set("EFGIJ"), 87: set("DEIJL")}
SO = list(TS)
# Realized third-place -> T-slot assignment, to be pinned from FIFA's official
# Round-of-32 bracket once the group stage concludes (~27 June 2026). Map each
# T-slot match number to the GROUP whose third-placed team fills it, e.g.
#   REALIZED_THIRDS = {74:"A", 77:"C", 79:"F", 80:"K", 81:"B", 82:"G", 85:"E", 87:"D"}
# While empty, assign() falls back to a deterministic backtracking fill, which the
# baseline forecast is robust to (measured: champion/advance probs unchanged within
# Monte-Carlo noise). Read the realized slotting off observed groups, and cross-check
# it against FIFA's announced bracket, with realized_bracket(<group results>).
REALIZED_THIRDS = {}
R32 = {74: ("E1", "T74"), 77: ("I1", "T77"), 73: ("A2", "B2"), 75: ("F1", "C2"),
       76: ("C1", "F2"), 78: ("E2", "I2"), 79: ("A1", "T79"), 80: ("L1", "T80"),
       83: ("K2", "L2"), 84: ("H1", "J2"), 81: ("D1", "T81"), 82: ("G1", "T82"),
       86: ("J1", "H2"), 88: ("D2", "G2"), 85: ("B1", "T85"), 87: ("K1", "T87")}
R16 = {89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
       93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87)}
QF = {97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96)}
SF = {101: (97, 98), 102: (99, 100)}
KO_TABLES = [(R16, False), (QF, True), (SF, True)]


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
    """Map the 8 qualifying third-place groups to the 8 T-slots. Once the group
    stage is played, REALIZED_THIRDS pins FIFA's official slotting; otherwise a
    deterministic backtracking fills the slots. The old code shuffled candidates
    randomly, so a given third-placed team landed in many different slots across
    Monte-Carlo iterations and a recorded third-place R32 result was accepted in
    only a fraction of them (see archive/docs_superpowers KO-conditioning issue)."""
    if REALIZED_THIRDS and set(REALIZED_THIRDS.values()) == set(q):
        return dict(REALIZED_THIRDS)

    def bt(i, used):
        if i == len(SO):
            return {}
        for g in sorted(g for g in q if g not in used and g in TS[SO[i]]):
            r = bt(i + 1, used | {g})
            if r is not None:
                r[SO[i]] = g
                return r
        return None
    return bt(0, set())


def realized_bracket(results, seed=2026):
    """Deterministic R32 slotting for FULLY-OBSERVED group results. Returns
    (slots, assignment): slots maps every R32 entry slot ('A1','T79',...) to a
    team; assignment maps each T-slot match number to its group letter. Used to
    build the KO acceptance test, and on ~27 June to read the realized third-place
    slotting off the final group table (cross-check against FIFA's bracket before
    pinning REALIZED_THIRDS)."""
    random.seed(seed)
    g_obs = {int(k): v for k, v in results.get("group", {}).items()}
    pos, thirds = {}, {}
    for grp in "ABCDEFGHIJKL":
        st = defaultdict(lambda: [0, 0, 0])
        for row in GROUPS[grp]:
            m = ROW_MATCH[row]
            lh, la, home, away = RATES[row]
            hg, ag = g_obs[m]
            for t, f, gg in ((home, hg, ag), (away, ag, hg)):
                st[t][1] += f - gg
                st[t][2] += f
                st[t][0] += 3 if f > gg else (1 if f == gg else 0)
        o = sorted(st, key=lambda t: (*st[t], random.random()), reverse=True)
        pos[f"{grp}1"], pos[f"{grp}2"] = o[0], o[1]
        thirds[grp] = (o[2], tuple(st[o[2]]))
    rk = sorted(thirds, key=lambda g: (*thirds[g][1], random.random()), reverse=True)
    am = assign(rk[:8]) or assign(rk[:7] + [rk[8]])
    slots = dict(pos)
    for m_, g_ in am.items():
        slots[f"T{m_}"] = thirds[g_][0]
    return slots, am


def conditional_probs(results, N=50000, seed=2026, ratings=None):
    """Return {team: {stage: prob}} given observed results (group + ko).
    ratings: optional {team: Elo} override — group scorelines then come from
    learn.lambda_expected and knockout winners from the Elo expectancy on these
    ratings (no host bonus), which is the Learning-track re-simulation. The
    default (None) is the locked market-rate path and is unchanged. A-vs-B
    contract: BOTH tracks of a two-track comparison must use ratings= (frozen
    leg = baseline_2026()), never one leg through the default market path."""
    random.seed(seed)
    if ratings is not None:
        from learn import lambda_expected

        def _kw(a, b, late=False):     # late unused: no host bonus in ratings mode
            e = 1 / (1 + 10 ** (-(ratings[a] - ratings[b]) / 400))
            return a if random.random() < e else b
    else:
        _kw = kw
    g_obs = {int(k): v for k, v in results.get("group", {}).items()}
    ko_obs = {int(k): v for k, v in results.get("ko", {}).items()}
    reach = defaultdict(Counter)   # team -> stage(1..6) count; champion=6
    STAGES = {1: "advance_KO", 2: "R16", 3: "QF", 4: "SF", 5: "final", 6: "champion"}
    for _ in range(N):
        pos, thirds = {}, {}
        for grp in "ABCDEFGHIJKL":
            st = defaultdict(lambda: [0, 0, 0])
            for row in GROUPS[grp]:
                m = ROW_MATCH[row]
                lh, la, home, away = RATES[row]
                if m in g_obs:
                    hg, ag = g_obs[m]
                elif ratings is not None:
                    le_h, le_a = lambda_expected(ratings[home], ratings[away])
                    hg, ag = sample(le_h), sample(le_a)
                else:
                    hg, ag = sample(lh), sample(la)
                for t, f, gg in ((home, hg, ag), (away, ag, hg)):
                    st[t][1] += f - gg
                    st[t][2] += f
                    st[t][0] += 3 if f > gg else (1 if f == gg else 0)
            o = sorted(st, key=lambda t: (*st[t], random.random()), reverse=True)
            pos[f"{grp}1"], pos[f"{grp}2"] = o[0], o[1]
            thirds[grp] = (o[2], tuple(st[o[2]]))
        rk = sorted(thirds, key=lambda g: (*thirds[g][1], random.random()), reverse=True)
        am = assign(rk[:8]) or assign(rk[:7] + [rk[8]])
        if am is None:
            continue
        slots = dict(pos)
        inko = set(pos.values())
        for m_, g_ in am.items():
            slots[f"T{m_}"] = thirds[g_][0]
            inko.add(thirds[g_][0])
        for t in inko:
            reach[t][1] += 1
        W = {}
        for m, (s1, s2) in R32.items():
            a, b = slots[s1], slots[s2]
            W[m] = ko_obs[m] if (m in ko_obs and ko_obs[m] in (a, b)) else _kw(a, b)
            reach[W[m]][2] += 1
        for tab, late in KO_TABLES:
            stg = {89: 3, 93: 3, 91: 3, 95: 3, 90: 3, 94: 3, 92: 3, 96: 3,
                   97: 4, 98: 4, 99: 4, 100: 4, 101: 5, 102: 5}
            for m, (m1, m2) in tab.items():
                a, b = W[m1], W[m2]
                W[m] = ko_obs[m] if (m in ko_obs and ko_obs[m] in (a, b)) else _kw(a, b, late)
                reach[W[m]][stg[m]] += 1
        a, b = W[101], W[102]
        champ = ko_obs[104] if (104 in ko_obs and ko_obs[104] in (a, b)) else _kw(a, b, True)
        reach[champ][6] += 1

    out = {}
    for t in ELO:
        c = reach[t]
        # reach[t][s] already indicates "reached stage s" (cumulative), so the
        # probability of reaching stage s is c[s]/N directly -- summing s..6
        # would double-count deeper runs.
        out[t] = {STAGES[s]: round(c[s] / N, 4) for s in range(1, 7)}
    return out


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
    log_path = DATA / "results_log.json"
    results = json.loads(log_path.read_text()) if log_path.exists() else {"group": {}, "ko": {}}
    probs = conditional_probs(results, N=N)
    (DATA / "snapshot.json").write_text(json.dumps(probs, ensure_ascii=False, indent=1))
    top = sorted(probs.items(), key=lambda x: -x[1]["champion"])[:8]
    ng = len(results.get("group", {}))
    nk = len(results.get("ko", {}))
    print(f"conditioned on {ng} group + {nk} knockout results (N={N})")
    print("champion probabilities:")
    for t, d in top:
        print(f"  {t:<16} {d['champion']*100:5.1f}%")
