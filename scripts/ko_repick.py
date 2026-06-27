"""EV-optimal full knockout entry on the real R32 bracket (friends' pool).

The pool scores a forward bracket "only if your projected matchup occurs", so a
later-round pick's expected value is `P(your projected pair actually occupies the
slot) * per-match EV`. `optimize_entry` computes the GLOBALLY EV-optimal
internally-consistent bracket by exact dynamic programming over the bracket tree:
slot-occupancy probabilities are estimated once by Monte-Carlo of the real
bracket, then the DP chooses, bottom-up, the advancer at every match to maximise
total expected points. `build_entry` keeps the simpler GREEDY (per-match-myopic)
baseline for comparison — greedy is NOT optimal, because the advancer chosen at a
match changes both downstream reachability and the downstream matchup's EV.

Run AFTER the group stage, once condition.REALIZED_THIRDS is pinned. All advance
probabilities (EV term AND the Monte-Carlo winner sampler) use the single
ko_match_ev cascade model (90' -> extra time -> penalties), for coherence."""
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import condition as C
import ko_match_ev as kme

_ADV_CACHE = {}      # (home, away) -> P(home advances), cascade model
_EV_CACHE = {}       # (home, away, advancer_side) -> (ev, score)
_CACHE_EFF = None    # the eff vintage the caches were built for


def _ensure_cache(eff):
    """Invalidate the team-keyed caches when the ratings vintage (`eff`) changes,
    so evaluating two vintages (e.g. Frozen 1 vs Frozen 2) in one process never
    returns stale values. Identity check is safe: `eff` is held for the call."""
    global _CACHE_EFF
    if eff is not _CACHE_EFF:
        _ADV_CACHE.clear()
        _EV_CACHE.clear()
        _CACHE_EFF = eff

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
    _ensure_cache(eff)
    slots = real_r32_slots(results)
    winners, picks = {}, {}
    for m in sorted(C.R32) + sorted(C.R16) + sorted(C.QF) + sorted(C.SF):
        home, away = _pair(m, slots, winners)
        picks[m] = _pick(home, away, eff)
        winners[m] = picks[m]["advancer"]
    picks[FINAL] = _pick(winners[101], winners[102], eff)
    picks[THIRD] = _pick(picks[101]["loser"], picks[102]["loser"], eff)
    return {"champion": picks[FINAL]["advancer"], "picks": picks, "eff": eff}


def _cascade_advance(home, away, eff):
    """P(home advances) under the ko_match_ev cascade (90'->ET->penalties),
    memoised by ordered pair. This is the single advance model used everywhere —
    the EV term and the Monte-Carlo winner sampler — so they stay coherent."""
    key = (home, away)
    if key not in _ADV_CACHE:
        lh, la = kme.matchup_lambdas(home, away, eff)
        _ADV_CACHE[key], _ = kme.advance_probs(lh, la)
    return _ADV_CACHE[key]


def _pair_ev(home, away, advancer_side, eff):
    """(ev, score) for matchup (home, away) when the advancer is forced to
    `advancer_side` ('home'/'away'); memoised."""
    key = (home, away, advancer_side)
    if key not in _EV_CACHE:
        lh, la = kme.matchup_lambdas(home, away, eff)
        best = kme.ev_given_advancer(lh, la, advancer_side)
        _EV_CACHE[key] = (best["ev"], best["score"])
    return _EV_CACHE[key]


def _kw(home, away, eff, rng):
    """Sample a knockout winner from the cascade advance probability (coherent
    with the EV term), not the bare Elo logistic."""
    return home if rng.random() < _cascade_advance(home, away, eff) else away


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
    _ensure_cache(eff)
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


# --- Exact EV-optimal bracket (dynamic programming over the bracket tree) -------
#
# Under "scored only if your projected matchup occurs", a match m's expected
# contribution is reach(m) * ev(pair, advancer), where reach(m) factorises over
# m's two feeding sub-brackets (disjoint team sets => independent winners):
#   reach(m) = P(projected home occupies m's home feed)
#            * P(projected away occupies m's away feed).
# Those occupancy probabilities are properties of the REAL bracket alone (not of
# our projection), so we estimate them once by Monte-Carlo and then solve for the
# globally optimal consistent bracket by DP. Greedy maximises only the local
# advance term and is therefore suboptimal.

def _children(m):
    """The two feeding matches of m, or None for an R32 leaf."""
    for tbl in (C.R16, C.QF, C.SF, {FINAL: (101, 102)}):
        if m in tbl:
            return tbl[m]
    return None


def _winner_probs(slots, eff, N=20000, seed=2026):
    """P(team is the REAL winner of each feeding match), from N Monte-Carlo plays
    of the real bracket (winners ~ cascade). Returns {match: {team: prob}}."""
    feed = sorted(C.R32) + sorted(C.R16) + sorted(C.QF) + sorted(C.SF)
    rng = random.Random(seed)
    counts = {m: defaultdict(int) for m in feed}
    for _ in range(N):
        winners = {}
        for m in feed:
            if m in C.R32:
                x, y = C.R32[m]
                home, away = slots[x], slots[y]
            else:
                a, b = _children(m)
                home, away = winners[a], winners[b]
            w = home if rng.random() < _cascade_advance(home, away, eff) else away
            winners[m] = w
            counts[m][w] += 1
    return {m: {t: c / N for t, c in counts[m].items()} for m in feed}


def _dp(m, slots, eff, winp, memo):
    """{team_t: (value, (a, b))} for the subtree rooted at m: the best total
    expected points achievable within the subtree when m projects winner t
    upward, with (a, b) the children winners achieving it. value already includes
    m's own reach-weighted EV (reach = 1 for an R32 leaf, whose pair is fixed)."""
    if m in memo:
        return memo[m]
    kids = _children(m)
    out = {}
    if kids is None:                                  # R32 leaf: fixed pair
        x, y = C.R32[m]
        a, b = slots[x], slots[y]
        for t, side in ((a, "home"), (b, "away")):
            ev, _ = _pair_ev(a, b, side, eff)
            out[t] = (ev, (a, b))
    else:
        ca, cb = kids
        da, db = _dp(ca, slots, eff, winp, memo), _dp(cb, slots, eff, winp, memo)
        for a, (va, _) in da.items():
            wa = winp[ca].get(a, 0.0)
            for b, (vb, _) in db.items():
                reach = wa * winp[cb].get(b, 0.0)
                for t, side in ((a, "home"), (b, "away")):
                    ev, _ = _pair_ev(a, b, side, eff)
                    val = va + vb + reach * ev
                    if t not in out or val > out[t][0]:
                        out[t] = (val, (a, b))
    memo[m] = out
    return out


def _reconstruct(m, t, eff, memo, picks):
    """Walk the DP backpointers from match m (projecting winner t), filling
    `picks` with the chosen pick per match in the subtree."""
    a, b = memo[m][t][1]
    side = "home" if t == a else "away"
    ev, score = _pair_ev(a, b, side, eff)
    picks[m] = {"home": a, "away": b, "score": score, "advancer": t,
                "loser": b if t == a else a, "ev": ev}
    kids = _children(m)
    if kids is not None:
        ca, cb = kids
        _reconstruct(ca, a, eff, memo, picks)
        _reconstruct(cb, b, eff, memo, picks)


def optimize_entry(results, eff=None, N=20000, seed=2026):
    """Globally EV-optimal internally-consistent knockout entry, by exact DP over
    the bracket tree (slot-occupancy probabilities from N Monte-Carlo sims).
    Same return shape as build_entry; dominates the greedy build_entry."""
    if eff is None:
        eff = kme.load_live_eff()
    _ensure_cache(eff)
    slots = real_r32_slots(results)
    winp = _winner_probs(slots, eff, N=N, seed=seed)
    memo = {}
    root = _dp(FINAL, slots, eff, winp, memo)
    champion = max(root, key=lambda t: root[t][0])
    picks = {}
    _reconstruct(FINAL, champion, eff, memo, picks)
    # Third-place playoff: the two semifinal losers of the chosen bracket.
    th, ta = picks[101]["loser"], picks[102]["loser"]
    side = "home" if _cascade_advance(th, ta, eff) >= 0.5 else "away"
    ev, score = _pair_ev(th, ta, side, eff)
    adv = th if side == "home" else ta
    picks[THIRD] = {"home": th, "away": ta, "score": score, "advancer": adv,
                    "loser": ta if adv == th else th, "ev": ev}
    return {"champion": champion, "picks": picks, "eff": eff, "winp": winp}


def _value_under(entry, winp):
    """Total expected points of a consistent entry under occupancy `winp`, with
    reach factorised exactly (no Monte-Carlo noise). Excludes the third-place
    game (its feeds aren't in winp); used to compare brackets on one yardstick."""
    picks, total = entry["picks"], 0.0
    for m, p in picks.items():
        if m == THIRD:
            continue
        if m in C.R32:
            reach = 1.0
        else:
            ca, cb = _children(m)
            reach = winp[ca].get(p["home"], 0.0) * winp[cb].get(p["away"], 0.0)
        total += reach * p["ev"]
    return total


def render_report(entry, weights, results):
    """Markdown re-pick report: champion, reachability-weighted expected points,
    and every knockout pick (90' scoreline + advancer + reach weight + EV)."""
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
    ap.add_argument("-N", type=int, default=20000, help="Monte-Carlo sims")
    ap.add_argument("--greedy", action="store_true",
                    help="use the greedy baseline instead of the EV-optimal DP")
    ap.add_argument("--out", default=None, help="write the report to this path")
    a = ap.parse_args()
    if a.predicted:
        pr = json.loads((C.DATA / "predictions_realistic.json").read_text())
        results = {"group": {str(p["num"]): [p["hg"], p["ag"]]
                             for p in pr if str(p["stage"]).startswith("Group")},
                   "ko": {}}
    else:
        results = _load_results(a.results)
    entry = build_entry(results) if a.greedy else optimize_entry(results, N=a.N)
    weights = reach_weights(results, entry, N=a.N)
    report = render_report(entry, weights, results)
    # report the optimizer's exact edge over greedy (same occupancy yardstick)
    if not a.greedy:
        g = build_entry(results, eff=entry["eff"])
        gain = _value_under(entry, entry["winp"]) - _value_under(g, entry["winp"])
        report += f"\n_EV-optimal (DP) vs greedy baseline: +{gain:.2f} expected points._\n"
    if a.out:
        Path(a.out).write_text(report)
        print(f"wrote {a.out}")
    else:
        print(report)
