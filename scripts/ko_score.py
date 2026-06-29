"""Pool scoring for one knockout game against a bracket pick: the 90' three-tier
score (3 exact / 2 result+GD / 1 result) plus 1 for the advancer, gated on the
projected matchup actually occurring (a deep pick scores nothing otherwise)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from realism_backtest import score_321


def applies(pick, actual_home, actual_away):
    """True if the pick's projected pair is the slot's actual pair (orientation-free)."""
    return {pick["home"], pick["away"]} == {actual_home, actual_away}


def score_pick(pick, actual_90, advancer):
    """Points for `pick` (with 'disp' = predicted 90' [h,a], 'advancer') against the
    actual 90' score and advancer. Assumes the matchup applies (caller gates)."""
    line = score_321(tuple(pick["disp"]), actual_90[0], actual_90[1])
    return line + (1 if pick["advancer"] == advancer else 0)
