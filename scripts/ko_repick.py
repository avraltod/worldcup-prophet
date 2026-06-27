"""EV-optimal full knockout entry on the real R32 bracket (friends' pool).

Derives the real 32-team R32 field from condition.realized_bracket, then
forward-propagates the EV-optimal advancer (per ko_match_ev) through R16, QF, SF,
Final, and the third-place playoff, producing one internally-consistent entry.
'Greedy by advance probability' is the reachability-optimal advancer choice for
the 'scored only if the projected matchup occurs' rule: advancing the stronger
team maximizes the chance later picks stay live. Run AFTER the group stage, once
REALIZED_THIRDS is pinned."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import condition as C
import ko_match_ev as kme

FINAL, THIRD = 104, 103


def real_r32_slots(results):
    """{'A1','A2','T74',...} -> team, from the fully-observed group results."""
    slots, _am = C.realized_bracket(results)
    return slots


def _pair(m, slots, winners):
    if m in C.R32:
        x, y = C.R32[m]
        return slots[x], slots[y]
    table = C.R16 if m in C.R16 else (C.QF if m in C.QF else C.SF)
    a, b = table[m]
    return winners[a], winners[b]


def _pick(home, away, eff):
    lh, la = kme.matchup_lambdas(home, away, eff)
    best = kme.match_ev(lh, la)
    adv = home if best["advancer"] == "home" else away
    loser = away if adv == home else home
    return {"home": home, "away": away, "score": best["score"],
            "advancer": adv, "loser": loser, "ev": best["ev"]}


def build_entry(results, eff=None):
    if eff is None:
        eff = kme.load_live_eff()      # Track B: all post-group-stage information
    slots = real_r32_slots(results)
    winners, picks = {}, {}
    for m in sorted(C.R32) + sorted(C.R16) + sorted(C.QF) + sorted(C.SF):
        home, away = _pair(m, slots, winners)
        picks[m] = _pick(home, away, eff)
        winners[m] = picks[m]["advancer"]
    picks[FINAL] = _pick(winners[101], winners[102], eff)
    picks[THIRD] = _pick(picks[101]["loser"], picks[102]["loser"], eff)
    return {"champion": picks[FINAL]["advancer"], "picks": picks, "eff": eff}


import random


def _kw(home, away, eff, rng):
    """Sample a knockout winner from Track B effective Elo (Elo win-expectancy)."""
    e = 1.0 / (1.0 + 10 ** (-(eff[home] - eff[away]) / 400.0))
    return home if rng.random() < e else away


def _simulate_bracket_winners(slots, eff, rng):
    """One Monte-Carlo play-through of the real KO bracket; returns {match: (home,
    away, winner)}, winners sampled from Track B effective Elo `eff`."""
    out, winners = {}, {}
    for m in sorted(C.R32) + sorted(C.R16) + sorted(C.QF) + sorted(C.SF):
        if m in C.R32:
            x, y = C.R32[m]
            home, away = slots[x], slots[y]
        else:
            table = C.R16 if m in C.R16 else (C.QF if m in C.QF else C.SF)
            a, b = table[m]
            home, away = winners[a], winners[b]
        w = _kw(home, away, eff, rng)
        out[m], winners[m] = (home, away, w), w
    out[FINAL] = (winners[101], winners[102], _kw(winners[101], winners[102], eff, rng))
    return out


def reach_weights(results, entry, N=20000, seed=2026):
    """For each KO match m, P(the entry's projected pair occupies m), from N
    winner-only simulations of the real bracket (Track B `eff`). R32 pairs are
    fixed (1.0); the third-place pair is gated on both projected semifinal losers
    reaching it."""
    slots = real_r32_slots(results)
    picks, eff = entry["picks"], entry["eff"]
    rng = random.Random(seed)
    hits = {m: 0 for m in picks}
    for _ in range(N):
        sim = _simulate_bracket_winners(slots, eff, rng)
        sim_pairs = {m: {sim[m][0], sim[m][1]} for m in sim}
        for m in picks:
            if m == THIRD:
                losers = set()
                for s in C.SF:
                    h, a, w = sim[s]
                    losers.add(a if w == h else h)
                if {picks[m]["home"], picks[m]["away"]} == losers:
                    hits[m] += 1
            elif m in sim_pairs and sim_pairs[m] == {picks[m]["home"], picks[m]["away"]}:
                hits[m] += 1
    return {m: (1.0 if m in C.R32 else hits[m] / N) for m in picks}


def expected_points(entry, weights):
    return sum(weights[m] * entry["picks"][m]["ev"] for m in entry["picks"])


def render_report(entry, weights, results, original=None):
    """Markdown re-pick report. `original` (optional) is {match_no: 'desc'} of the
    locked picks, to flag now-void (eliminated) slots."""
    picks = entry["picks"]
    rounds = [("Round of 32", sorted(C.R32)), ("Round of 16", sorted(C.R16)),
              ("Quarter-finals", sorted(C.QF)), ("Semi-finals", sorted(C.SF)),
              ("Third place", [THIRD]), ("Final", [FINAL])]
    lines = ["# KO pool re-pick - proposed entry", "",
             f"**Champion:** {entry['champion']}",
             f"**Expected points (reachability-weighted):** "
             f"{expected_points(entry, weights):.2f}", ""]
    for name, ms in rounds:
        lines.append(f"## {name}")
        lines.append("| Match | Pick (90') | Advances | Reach wt | EV |")
        lines.append("|---|---|---|---|---|")
        for m in ms:
            p = picks[m]
            h, a = p["score"]
            lines.append(f"| {m} {p['home']} v {p['away']} | {h}-{a} | "
                         f"{p['advancer']} | {weights[m]:.2f} | {p['ev']:.2f} |")
        lines.append("")
    return "\n".join(lines)


def _load_results(path):
    import json
    if path:
        return json.loads(Path(path).read_text())
    # default: live results log (use AFTER the group stage + REALIZED_THIRDS pin)
    return json.loads((C.DATA / "results_log.json").read_text())


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(description="EV-optimal KO pool re-pick")
    ap.add_argument("--results", default=None,
                    help="results JSON (default data/results_log.json)")
    ap.add_argument("--predicted", action="store_true",
                    help="dry-run on the model's predicted full-group results")
    ap.add_argument("-N", type=int, default=20000, help="reachability sims")
    ap.add_argument("--out", default=None, help="write the report to this path")
    a = ap.parse_args()
    if a.predicted:
        pr = json.loads((C.DATA / "predictions_realistic.json").read_text())
        results = {"group": {str(p["num"]): [p["hg"], p["ag"]]
                             for p in pr if str(p["stage"]).startswith("Group")},
                   "ko": {}}
    else:
        results = _load_results(a.results)
    entry = build_entry(results)
    weights = reach_weights(results, entry, N=a.N)
    report = render_report(entry, weights, results)
    if a.out:
        Path(a.out).write_text(report)
        print(f"wrote {a.out}")
    else:
        print(report)
