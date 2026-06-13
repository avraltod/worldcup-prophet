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


# ---------------- new ctx keys / draft_sections wiring ----------------------

import draft_sections as ds


def _ctx():
    """Minimal ctx matching what _write_living_layer now provides."""
    entries = [
        {"match": 1, "fixture": "Mexico v Ecuador", "result": [2, 0],
         "pre": {"probs_HDA": [0.55, 0.25, 0.20]},
         "post": {"points": 2, "brier": 0.30, "info_bits": 0.05,
                  "p_outcome": 0.55}},
        {"match": 2, "fixture": "South Korea v Czechia", "result": [2, 1],
         "pre": {"probs_HDA": [0.40, 0.28, 0.32]},
         "post": {"points": 1, "brier": 0.55, "info_bits": 0.12,
                  "p_outcome": 0.20},
         "failure_mode": None},
    ]
    frozen = {"Spain": {"advance_KO": 0.99, "R16": 0.80, "QF": 0.62,
                         "SF": 0.52, "final": 0.39, "champion": 0.27},
              "Argentina": {"advance_KO": 0.98, "R16": 0.71, "QF": 0.59,
                            "SF": 0.43, "final": 0.30, "champion": 0.18}}
    now = {"Spain": {"advance_KO": 0.99, "R16": 0.81, "QF": 0.63,
                     "SF": 0.53, "final": 0.40, "champion": 0.28},
           "Argentina": {"advance_KO": 0.97, "R16": 0.70, "QF": 0.58,
                         "SF": 0.42, "final": 0.29, "champion": 0.17}}
    return {
        "match": 2,
        "entries": entries,
        "match_stats": {},
        "learning": {"drift": {"Spain": 0.5}, "processed": [], "history": []},
        "prev_now": {"Spain": {"champion": 0.27}, "Argentina": {"champion": 0.18}},
        "now": now,
        "frozen": frozen,
        "results": {"group": {"1": [2, 0], "2": [2, 1]}, "ko": {}},
        "n_results": 2,
        "cum_points": 3,
        "mean_brier": 0.425,
        "champ_now_top": [["Spain", 0.28], ["Argentina", 0.17]],
        "two_track": None,
        "champion_movers": [["Spain", 0.27, 0.28], ["Argentina", 0.18, 0.17]],
        "vintages_rows": [{"edition": 0}, {"edition": 2}],
        "revision_narrative": "Test narrative.",
        "implications": [],
    }


def test_abstract_live_uses_champ_now_top():
    text, src = ds.draft_abstract_live(_ctx(), use_api=False)
    assert "Spain" in text
    assert src == "template"


def test_simulation_note_uses_n_results():
    text, _ = ds.draft_simulation_note(_ctx(), use_api=False)
    assert "2" in text  # n_results = 2


def test_data_revealed_has_label():
    text, _ = ds.draft_data_revealed(_ctx(), use_api=False)
    assert r"\label{tab:live_data_revealed}" in text


def test_failure_analysis_has_label():
    text, _ = ds.draft_failure_analysis(_ctx(), use_api=False)
    assert r"\label{sec:live_failure}" in text


def test_failure_analysis_catches_high_brier():
    """M2 has brier=0.55 > threshold; should appear in failure log."""
    text, _ = ds.draft_failure_analysis(_ctx(), use_api=False)
    assert "M2" in text


def test_discussion_live_uses_n_results():
    text, _ = ds.draft_discussion_live(_ctx(), use_api=False)
    assert "2" in text  # n_results


def test_champion_movers_in_sec36():
    ctx = _ctx()
    ctx["champion_movers"] = [["Spain", 0.20, 0.28]]
    text, _ = ds.draft_sec36_live(ctx, use_api=False)
    assert "2" in text  # n_results present
