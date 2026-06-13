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


def test_conditional_probs_ratings_override():
    import condition as cond
    import live_state as lst
    base = lst.baseline_2026()
    out = cond.conditional_probs({"group": {}, "ko": {}}, N=300, seed=7,
                                 ratings=base)
    assert set(out) == set(cond.ELO)
    assert abs(sum(d["champion"] for d in out.values()) - 1.0) < 1e-6
    # a recorded result is still respected under ratings mode
    out2 = cond.conditional_probs({"group": {"1": [9, 0]}, "ko": {}}, N=300,
                                  seed=7, ratings=base)
    assert out2["Mexico"]["advance_KO"] >= out["Mexico"]["advance_KO"]
    # sensitivity: the override must actually drive the simulation — +75 Elo
    # to Spain moves its champion probability far outside MC noise
    boosted = dict(base); boosted["Spain"] = base["Spain"] + 75
    out3 = cond.conditional_probs({"group": {}, "ko": {}}, N=300, seed=7,
                                  ratings=boosted)
    assert out3["Spain"]["champion"] > out["Spain"]["champion"] + 0.03


def test_conditional_probs_default_path_unchanged():
    import condition as cond
    a = cond.conditional_probs({"group": {}, "ko": {}}, N=300, seed=7)
    b = cond.conditional_probs({"group": {}, "ko": {}}, N=300, seed=7,
                               ratings=None)
    assert a == b


def test_south_korea_advance_jumps_after_m2_win():
    """M2: South Korea 2-1 Czechia should lift South Korea advance_KO by >=15pp."""
    frozen = json.loads((ROOT / "data" / "frozen_stage_probs.json").read_text())["stages"]
    results_m2 = {"group": {"1": [2, 0], "2": [2, 1]}, "ko": {}}
    now = C.conditional_probs(results_m2, N=20000, seed=42)
    frozen_ko = frozen.get("South Korea", {}).get("advance_KO", 0.5)
    now_ko = now.get("South Korea", {}).get("advance_KO", 0.0)
    assert now_ko > frozen_ko + 0.15, (
        f"South Korea advance_KO should jump >15pp after M2 win; "
        f"frozen={frozen_ko:.3f} now={now_ko:.3f} delta={now_ko-frozen_ko:+.3f}")


def test_paraguay_advance_drops_after_m4_loss():
    """M4: US 4-1 Paraguay should cut Paraguay's advance_KO by >=15pp."""
    frozen = json.loads((ROOT / "data" / "frozen_stage_probs.json").read_text())["stages"]
    results_m4 = {"group": {"1": [2, 0], "2": [2, 1], "3": [1, 1], "4": [4, 1]}, "ko": {}}
    now = C.conditional_probs(results_m4, N=20000, seed=42)
    frozen_ko = frozen.get("Paraguay", {}).get("advance_KO", 0.5)
    now_ko = now.get("Paraguay", {}).get("advance_KO", 0.5)
    assert now_ko < frozen_ko - 0.15, (
        f"Paraguay advance_KO should drop >15pp after M4 loss; "
        f"frozen={frozen_ko:.3f} now={now_ko:.3f} delta={now_ko-frozen_ko:+.3f}")
