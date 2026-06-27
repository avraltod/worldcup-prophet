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


# --- realistic scoreline readout (let real scores + penalty draws happen) -------

def test_realistic_pick_score_decisive_home_favorite():
    hg, ag, pen = kr.realistic_pick_score(2.1, 0.4, "home")
    assert not pen and hg > ag            # clear favorite wins decisively in 90'


def test_realistic_pick_score_even_match_is_a_draw_to_penalties():
    hg, ag, pen = kr.realistic_pick_score(1.2, 1.2, "home")
    assert pen and hg == ag               # genuine toss-up: level 90', decided on pens


def test_realistic_pick_score_away_favorite():
    hg, ag, pen = kr.realistic_pick_score(0.4, 2.1, "away")
    assert not pen and ag > hg            # away advancer takes the higher score


def test_entry_picks_carry_realistic_readout():
    entry = kr.build_entry(_predicted_results())
    for m, p in entry["picks"].items():
        assert "disp" in p and "pen" in p
        hg, ag = p["disp"]
        assert 0 <= hg <= 8 and 0 <= ag <= 8
        if p["pen"]:
            assert hg == ag              # a penalty draw is level in regulation
        else:
            wg = hg if p["advancer"] == p["home"] else ag
            lg = ag if p["advancer"] == p["home"] else hg
            assert wg > lg               # the displayed winner is the optimizer's advancer


def test_readout_does_not_change_the_optimizer():
    # attaching the realistic readout must not move any advancer, champion, or EV
    results = _predicted_results()
    eff = kme.load_live_eff()
    entry = kr.build_entry(results, eff=eff)
    for m, p in entry["picks"].items():
        ev_yardstick = kme.match_ev(*kme.matchup_lambdas(p["home"], p["away"], eff))["ev"]
        assert abs(p["ev"] - ev_yardstick) < 1e-9   # ev is still the EV-optimal yardstick


def test_render_report_shows_realistic_score_and_penalty_draws():
    results = _predicted_results()
    entry = kr.build_entry(results)
    weights = kr.reach_weights(results, entry, N=500, seed=1)
    text = kr.render_report(entry, weights, results)
    # the Final's rendered scoreline is the realistic readout, not the EV pick
    hg, ag = entry["picks"][104]["disp"]
    assert f"{hg}-{ag}" in text
    # any penalty-decided pick is flagged as such
    if any(p["pen"] for p in entry["picks"].values()):
        assert "pens" in text.lower()
