"""Pool scoring for one knockout game against a bracket pick: the 90' three-tier
score (3 exact / 2 result+GD / 1 result) plus 1 for the advancer. The scoreline
tier is graded ORIENTED TO THE PICKED TEAM (pick['advancer']) whenever that team
is in the game; it is NOT gated on the projected opponent (a pick that wins
against a different opponent than projected still scores its real value). If the
picked team isn't in the game the scoreline tier scores 0."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from realism_backtest import score_321


def applies(pick, actual_home, actual_away):
    """True if the pick's projected pair is the slot's actual pair (orientation-free).
    Retained for reference; NO LONGER used to gate scoring."""
    return {pick["home"], pick["away"]} == {actual_home, actual_away}


def score_pick(pick, actual_home, actual_away, actual_90, actual_advancer):
    """Pool KO points for `pick` against the actual game, NOT gated on the
    opponent. The 90' scoreline tier (score_321) is graded oriented to the picked
    team (pick['advancer']); if that team isn't in the game the scoreline scores
    0. Plus 1 if the picked advancer is the actual advancer."""
    adv = pick["advancer"]
    adv_pt = 1 if adv == actual_advancer else 0
    line = 0
    if adv in (actual_home, actual_away):
        pg = pick["disp"][0] if adv == pick["home"] else pick["disp"][1]
        po = pick["disp"][1] if adv == pick["home"] else pick["disp"][0]
        ag = actual_90[0] if adv == actual_home else actual_90[1]
        ao = actual_90[1] if adv == actual_home else actual_90[0]
        line = score_321((pg, po), ag, ao)
    return line + adv_pt
