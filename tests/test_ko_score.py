import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ko_score as ks

PICK = {"home": "Germany", "away": "Paraguay", "disp": [2, 0], "advancer": "Germany"}


def test_exact_score_plus_advancer():
    # pick Spain 2-1 (home), actual Spain won 2-1 -> 3 (exact) + 1 (advancer) = 4
    pick = {"home": "Spain", "away": "Croatia", "disp": [2, 1], "advancer": "Spain"}
    assert ks.score_pick(pick, actual_home="Spain", actual_away="Croatia",
                         actual_90=[2, 1], actual_advancer="Spain") == 4


def test_opponent_swap_win_still_scores():
    # picked France to beat Germany 2-0; France actually played (and beat)
    # Paraguay 1-0. NOT opponent-gated: winner tier 1 + advancer 1 = 2.
    pick = {"home": "France", "away": "Germany", "disp": [2, 0], "advancer": "France"}
    assert ks.score_pick(pick, actual_home="France", actual_away="Paraguay",
                         actual_90=[1, 0], actual_advancer="France") == 2


def test_wrong_advancer_exact_draw_scores_line_only():
    # pick a 2-2 draw with advancer A; actual 2-2 draw but B advanced (ET/pens):
    # scoreline tier 3 + advancer 0 = 3.
    pick = {"home": "A", "away": "B", "disp": [2, 2], "advancer": "A"}
    assert ks.score_pick(pick, actual_home="A", actual_away="B",
                         actual_90=[2, 2], actual_advancer="B") == 3


def test_picked_team_absent_scores_zero():
    # picked Spain, but Spain is not in the actual pair -> 0
    pick = {"home": "Spain", "away": "Croatia", "disp": [2, 0], "advancer": "Spain"}
    assert ks.score_pick(pick, actual_home="France", actual_away="Paraguay",
                         actual_90=[1, 0], actual_advancer="France") == 0


def test_result_gd_wrong_plus_advancer():
    # predicted 2-0, actual 1-0: GD wrong, result right -> 1, +1 advancer = 2
    assert ks.score_pick(PICK, actual_home="Germany", actual_away="Paraguay",
                         actual_90=[1, 0], actual_advancer="Germany") == 2


def test_result_and_gd_correct_plus_advancer():
    # predicted 3-1, actual 2-0: home win, GD=2 in both -> score_321 = 2, +1 adv = 3
    pick = {"home": "Germany", "away": "Paraguay", "disp": [3, 1], "advancer": "Germany"}
    assert ks.score_pick(pick, actual_home="Germany", actual_away="Paraguay",
                         actual_90=[2, 0], actual_advancer="Germany") == 3


def test_orientation_when_picked_team_is_away():
    # picked team is the actual AWAY team: pick Germany (away) to win by 2 (disp
    # oriented home=Paraguay, away=Germany -> [0,2]); actual Paraguay 0 Germany 1.
    pick = {"home": "Paraguay", "away": "Germany", "disp": [0, 2], "advancer": "Germany"}
    # Germany won 1-0 (away): result tier 1 + advancer 1 = 2
    assert ks.score_pick(pick, actual_home="Paraguay", actual_away="Germany",
                         actual_90=[0, 1], actual_advancer="Germany") == 2


def test_matchup_gate_helper_still_defined():
    # applies() is retained (no longer used for gating) and orientation-free
    assert ks.applies(PICK, actual_home="Germany", actual_away="Sweden") is False
    assert ks.applies(PICK, actual_home="Paraguay", actual_away="Germany") is True
