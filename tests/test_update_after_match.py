import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import update_after_match as uam

TRAJ = [
    {"phase": "pre", "match": 1, "kickoff": "2026-06-11T19:00:00Z",
     "champion": {"Spain": 0.2711, "Argentina": 0.1768},
     "market_champion": {"Spain": 0.164}, "info_bits": 0.0,
     "result": None, "performance": None},
    {"phase": "post", "match": 1, "kickoff": "2026-06-11T19:00:00Z",
     "champion": {"Spain": 0.2711, "Argentina": 0.1815}, "info_bits": 0.0011,
     "result": [2, 0],
     "performance": {"points": 1, "ev_points": 0.855, "p_outcome": 0.6718, "brier": 0.1655}},
]
EXP = [{"match": 1, "group": "A", "home": "Mexico", "away": "South Africa",
        "pick": [2, 1], "probs_HDA": [0.6718, 0.2087, 0.1193], "lh": 1.9, "la": 0.65}]

def test_pending_matches_are_finalized_but_undocumented(tmp_path):
    idx = tmp_path / "index.json"
    pending = uam.pending_matches(TRAJ, idx)
    assert pending == [1]

def test_re_ev_delta_uses_ev_pick():
    # realistic pick 2-1 scored 1; EV pick 1-0 also scores 1 vs 2-0 -> delta 0
    d = uam.re_ev_delta_for(EXP[0], [2, 0], realistic_points=1)
    assert d == 0

def test_re_ev_delta_nonzero_when_tiers_differ():
    # ev pick (1,0) vs actual 2-1 scores 2 (correct result + GD); realistic scored 3 (exact) -> delta +1
    exp = {"lh": 1.9, "la": 0.65}
    d = uam.re_ev_delta_for(exp, [2, 1], realistic_points=3)
    assert d == 1

def test_build_full_entry_attaches_interpretation_and_failure_tag(tmp_path):
    e = uam.build_full_entry(1, TRAJ, EXP, forecast_commit="abc1234",
                             documented_at="2026-06-11T21:10:58Z", use_api=False)
    assert e["interpretation"]                      # non-empty (templated)
    assert e["interpretation_source"] == "template"
    assert e["failure_mode"] in (None, *uam.mb.FAILURE_MODES)


# ---------------- live-edition helpers (conditioning set, group state) -------

TRAJ3 = TRAJ + [
    {"phase": "post", "match": 2, "kickoff": "2026-06-12T02:00:00Z",
     "champion": {"Spain": 0.2693}, "info_bits": 0.0008, "result": [2, 1],
     "performance": {"points": 0, "ev_points": 0.7428, "p_outcome": 0.3611,
                     "brier": 0.6128}},
    {"phase": "post", "match": 95, "kickoff": "2026-07-08T00:00:00Z",
     "champion": {"Spain": 0.30}, "info_bits": 0.2, "result": [2, 1],
     "winner": "Argentina", "performance": None},
]


def test_results_through_filters_by_match_number():
    r1 = uam.results_through(TRAJ3, 1)
    assert r1["group"] == {"1": [2, 0]} and r1["ko"] == {}
    r2 = uam.results_through(TRAJ3, 2)
    assert set(r2["group"]) == {"1", "2"}


def test_results_through_includes_ko_only_with_winner():
    r = uam.results_through(TRAJ3, 104)
    assert r["ko"] == {"95": "Argentina"}
    no_winner = [dict(x) for x in TRAJ3]
    no_winner[-1].pop("winner")
    assert uam.results_through(no_winner, 104)["ko"] == {}


def test_group_state_standings_arithmetic():
    state = uam.group_state({"group": {"1": [2, 0], "2": [2, 1]}, "ko": {}})
    # new behaviour: all 12 groups returned; Group A has played=2
    grp_a = next(g for g in state if g["group"] == "A")
    assert len(state) == 12
    assert grp_a["played"] == 2 and grp_a["total"] == 6
    rows = {r["team"]: (r["Pts"], r["GF"] - r["GA"]) for r in grp_a["rows"]}
    assert rows["Mexico"] == (3, 2)
    assert rows["South Korea"] == (3, 1)
    assert rows["Czechia"] == (0, -1)
    assert rows["South Africa"] == (0, -2)
    # sorted by points then GD
    assert [r["team"] for r in grp_a["rows"]][:2] == ["Mexico", "South Korea"]
    # unplayed groups are present with played=0
    unplayed = [g for g in state if g["played"] == 0]
    assert len(unplayed) == 11
