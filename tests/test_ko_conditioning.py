"""Acceptance test for the knockout third-place conditioning fix.

The bug: condition.assign() slotted third-placed teams into R32 T-slots
randomly per Monte-Carlo iteration, so recording a third-place R32 result was
accepted in only ~10-70% of iterations and the champion/stage trajectory barely
moved. With deterministic slotting, recording a T-slot winner sends that team to
the R16 and eliminates its opponent in the large majority of iterations.

This stands in a fully-observed group stage using the model's own predicted
scorelines, which exercises the deterministic assign() the same way the pinned
FIFA table (condition.REALIZED_THIRDS, filled ~27 June) will. The recorded team
reaches the R16 with prob ~0.85 rather than exactly 1.0 here only because the
synthetic group results leave some cross-group third-place ranking ties (broken
randomly in condition.py); that residual is unrelated to the assign bug and
shrinks once real, cleanly-ordered group results and REALIZED_THIRDS are in.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import condition as C

N = 20000


def _predicted_groups():
    pr = json.loads((ROOT / "data" / "predictions_realistic.json").read_text())
    return {str(p["num"]): [p["hg"], p["ag"]]
            for p in pr if str(p["stage"]).startswith("Group")}


def _group_points(groups, g):
    st = defaultdict(lambda: [0, 0, 0])
    for row in C.GROUPS[g]:
        m = C.ROW_MATCH[row]
        _, _, home, away = C.RATES[row]
        hg, ag = groups[str(m)]
        for t, f, gg in ((home, hg, ag), (away, ag, hg)):
            st[t][0] += 3 if f > gg else (1 if f == gg else 0)
    return sorted((st[t][0] for t in st), reverse=True)


def test_third_place_r32_winner_reaches_R16():
    groups = _predicted_groups()
    slots, am = C.realized_bracket({"group": groups, "ko": {}})

    # pick a T-slot whose third-placer is unambiguous within its group
    # (3rd strictly between 2nd and 4th on points), to isolate the assign fix
    m = next(mm for mm in sorted(am)
             if (lambda p: p[1] > p[2] > p[3])(_group_points(groups, am[mm])))
    seed_slot, third_slot = C.R32[m]
    third, opponent = slots[third_slot], slots[seed_slot]

    base = C.conditional_probs({"group": groups, "ko": {}}, N=N)
    after = C.conditional_probs({"group": groups, "ko": {str(m): third}}, N=N)

    # deterministic slotting restores the conditioning response the bug suppressed:
    # the recorded winner now reaches the R16 in the large majority of iterations,
    # its opponent is largely eliminated, and the move is far larger than the
    # near-zero the random assign produced.
    assert after[third]["R16"] > 0.80, (third, base[third]["R16"], after[third]["R16"])
    assert after[opponent]["R16"] < 0.20, (opponent, after[opponent]["R16"])
    assert after[third]["R16"] - base[third]["R16"] > 0.50


def test_baseline_unchanged_by_deterministic_assign():
    # deterministic slotting must not move the locked pre-registered baseline
    base = C.conditional_probs({"group": {}, "ko": {}}, N=N)
    assert 0.24 < base["Spain"]["champion"] < 0.30           # ~27%, within MC noise
    assert base["Argentina"]["champion"] > base["France"]["champion"]
