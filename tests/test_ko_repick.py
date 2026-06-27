import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ko_repick as kr
import ko_match_ev as kme
import condition as C


def _predicted_results():
    pr = json.loads((ROOT / "data" / "predictions_realistic.json").read_text())
    groups = {str(p["num"]): [p["hg"], p["ag"]]
              for p in pr if str(p["stage"]).startswith("Group")}
    return {"group": groups, "ko": {}}


def test_optimizer_complete_consistent_and_dominates_greedy():
    results = _predicted_results()
    eff = kme.load_live_eff()
    opt = kr.optimize_entry(results, eff=eff, N=4000, seed=1)
    picks = opt["picks"]
    # same structural invariants as the greedy entry
    assert set(picks) == set(C.R32) | set(C.R16) | set(C.QF) | set(C.SF) | {103, 104}
    for m, (fa, fb) in C.R16.items():
        assert {picks[m]["home"], picks[m]["away"]} == \
               {picks[fa]["advancer"], picks[fb]["advancer"]}
    assert opt["champion"] == picks[104]["advancer"]
    # exact dominance: under the optimizer's own occupancy, the DP bracket scores
    # at least as high as greedy (no Monte-Carlo noise in this comparison)
    greedy = kr.build_entry(results, eff=eff)
    winp = opt["winp"]
    assert kr._value_under(opt, winp) + 1e-9 >= kr._value_under(greedy, winp)


def test_entry_is_complete_and_consistent():
    entry = kr.build_entry(_predicted_results())
    picks = entry["picks"]
    expected_matches = set(C.R32) | set(C.R16) | set(C.QF) | set(C.SF) | {103, 104}
    assert set(picks) == expected_matches
    for m, p in picks.items():
        assert p["advancer"] in (p["home"], p["away"])
        h, a = p["score"]
        assert 0 <= h <= 8 and 0 <= a <= 8
    for m, (fa, fb) in C.R16.items():
        assert {picks[m]["home"], picks[m]["away"]} == {picks[fa]["advancer"], picks[fb]["advancer"]}
    assert entry["champion"] == picks[104]["advancer"]


def test_third_place_uses_semifinal_losers():
    entry = kr.build_entry(_predicted_results())
    picks = entry["picks"]
    sf_losers = set()
    for m in C.SF:
        loser = picks[m]["away"] if picks[m]["advancer"] == picks[m]["home"] else picks[m]["home"]
        sf_losers.add(loser)
    assert {picks[103]["home"], picks[103]["away"]} == sf_losers


def test_reach_weights_and_expected_points():
    results = _predicted_results()
    entry = kr.build_entry(results)
    weights = kr.reach_weights(results, entry, N=2000, seed=1)
    for m in C.R32:
        assert weights[m] == 1.0
    assert all(0.0 <= w <= 1.0 for w in weights.values())
    assert weights[101] <= 1.0 and weights[104] <= weights[101] + 1e-9
    ep = kr.expected_points(entry, weights)
    assert 0.0 < ep < 4.0 * 32


def test_render_report_mentions_champion_and_matches():
    results = _predicted_results()
    entry = kr.build_entry(results)
    weights = kr.reach_weights(results, entry, N=500, seed=1)
    text = kr.render_report(entry, weights, results)
    assert entry["champion"] in text
    assert "Expected points" in text
