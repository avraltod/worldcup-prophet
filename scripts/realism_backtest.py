"""Backtest the REALISTIC scoreline readout against the EV-optimal pick.

Both strategies share the identical model (Elo -> H/D/A -> Poisson fit); they
differ ONLY in how the fitted expected goals are turned into a printed scoreline:
  - EV pick:   argmax over scorelines of expected pool points under 3/2/1
               (scripts/ev321.best_pick).
  - Realistic: round the expected goals, preserving the modal result
               (scripts/realistic_scores.realistic).

For each real match of 2018 + 2022 we score BOTH under the true 3/2/1 rule and
measure exact-score hit rate and goal-closeness. This regenerates the evidence
the paper's Section 5.2 / fig:realism needs (the old fig compared the EV pick to
a random-sampling entry; this compares EV vs realistic, the actual design choice).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from poisson_model import fit_rates, pois, MAX_G
from ev321 import best_pick
from backtest import look, elo_hda, outcome, DATA, HOSTS


def realistic(lh, la, result):
    """Mirror of realistic_scores.realistic(): rounded goals preserving result."""
    if result == "D":
        k = round((lh + la) / 2)
        return k, k
    hg, ag = round(lh), round(la)
    if result == "H":
        if ag > hg:
            hg, ag = ag, hg
        if hg == ag:
            hg += 1
    else:
        if hg > ag:
            hg, ag = ag, hg
        if hg == ag:
            ag += 1
    return hg, ag


def score_321(pick, hg, ag):
    """Pool points for `pick` against actual (hg,ag): 3 exact / 2 result+GD / 1 result."""
    ph, pa = pick
    if (ph, pa) == (hg, ag):
        return 3
    if outcome(ph, pa) == outcome(hg, ag):
        return 2 if (ph - pa) == (hg - ag) else 1
    return 0


def goal_err(pick, hg, ag):
    return abs(pick[0] - hg) + abs(pick[1] - ag)


def run_year(year):
    elo = json.loads((DATA / f"elo_{year}.json").read_text())
    results = json.loads((DATA / f"results_{year}.json").read_text())
    host = HOSTS[year]
    n = 0
    ev = {"pts": 0, "exact": 0, "gerr": 0}
    re = {"pts": 0, "exact": 0, "gerr": 0}
    for m in results:
        eh, ea = look(elo, m["home"]), look(elo, m["away"])
        if eh is None or ea is None:
            continue
        ra = eh + (40 if m["home"] == host else 0)
        rb = ea + (40 if m["away"] == host else 0)
        ph, pd_, pa = elo_hda(ra, rb)
        lh, la = fit_rates(ph, pd_, pa)
        r = "H" if ph >= pd_ and ph >= pa else ("D" if pd_ >= pa else "A")
        hg, ag = m["hg"], m["ag"]
        n += 1
        evp = best_pick(lh, la)
        rep = realistic(lh, la, r)
        for tag, pick in (("ev", evp), ("re", rep)):
            d = ev if tag == "ev" else re
            d["pts"] += score_321(pick, hg, ag)
            d["exact"] += 1 if (pick[0], pick[1]) == (hg, ag) else 0
            d["gerr"] += goal_err(pick, hg, ag)
    return {"year": year, "n": n, "ev": ev, "re": re}


if __name__ == "__main__":
    tot = {"n": 0, "ev": {"pts": 0, "exact": 0, "gerr": 0},
           "re": {"pts": 0, "exact": 0, "gerr": 0}}
    per = []
    for year in (2018, 2022):
        r = run_year(year)
        per.append(r)
        tot["n"] += r["n"]
        for k in ("ev", "re"):
            for f in ("pts", "exact", "gerr"):
                tot[k][f] += r[k][f]
        print(f"=== {year} ({r['n']} matches) ===")
        for tag, name in (("ev", "EV-optimal"), ("re", "Realistic ")):
            d = r[tag]
            print(f"  {name}: {d['pts']} pts | {d['exact']} exact | "
                  f"{d['gerr']/r['n']:.3f} goal-err/match")
    e, rr, N = tot["ev"], tot["re"], tot["n"]
    print(f"\n=== POOLED 2018+2022 ({N} matches) ===")
    print(f"  EV-optimal: {e['pts']} pts | {e['exact']} exact | {e['gerr']/N:.3f} goal-err/match")
    print(f"  Realistic : {rr['pts']} pts | {rr['exact']} exact | {rr['gerr']/N:.3f} goal-err/match")
    print(f"  Δ realistic vs EV: {rr['pts']-e['pts']:+d} pts | "
          f"{rr['exact']-e['exact']:+d} exact | "
          f"goal-err {100*(rr['gerr']-e['gerr'])/e['gerr']:+.1f}%")
    (DATA / "realism_backtest.json").write_text(json.dumps(
        {"pooled": tot, "per_year": per}, indent=1))
    print("\nsaved data/backtest/realism_backtest.json")
