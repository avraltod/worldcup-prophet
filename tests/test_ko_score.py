import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ko_score as ks

PICK = {"home": "Germany", "away": "Paraguay", "disp": [2, 0], "advancer": "Germany"}

def test_exact_score_plus_advancer():
    # actual 2-0, Germany advances -> 3 (exact) + 1 (advancer) = 4
    assert ks.score_pick(PICK, actual_90=[2, 0], advancer="Germany") == 4

def test_result_gd_wrong_plus_advancer():
    # predicted 2-0, actual 1-0: GD wrong, result right -> 1, +1 advancer = 2
    assert ks.score_pick(PICK, actual_90=[1, 0], advancer="Germany") == 2

def test_result_and_gd_correct_plus_advancer():
    # predicted 3-1, actual 2-0: home win, GD=2 in both -> score_321 = 2, +1 adv = 3
    pick = {"home": "Germany", "away": "Paraguay", "disp": [3, 1], "advancer": "Germany"}
    assert ks.score_pick(pick, actual_90=[2, 0], advancer="Germany") == 3

def test_advancer_wrong_still_scores_the_line():
    # predicted 2-0, actual 1-1 (a draw), Paraguay advances -> line 0 + adv 0 = 0
    assert ks.score_pick(PICK, actual_90=[1, 1], advancer="Paraguay") == 0

def test_matchup_gate():
    # the pick's projected pair is Germany v Paraguay
    assert ks.applies(PICK, actual_home="Germany", actual_away="Sweden") is False
    assert ks.applies(PICK, actual_home="Paraguay", actual_away="Germany") is True
