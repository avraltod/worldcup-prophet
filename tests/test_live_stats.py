import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import live_stats as ls

E1 = {"match": 1, "result": [2, 0], "failure_mode": None,
      "pre": {"pick": [2, 1]},
      "post": {"points": 1, "brier": 0.1655},
      "champ_top_full": {"Spain": 0.2711, "Argentina": 0.1815}}
E2 = {"match": 2, "result": [1, 1], "failure_mode": "systematic_rating_error",
      "pre": {"pick": [1, 1]},
      "post": {"points": 3, "brier": 0.40},
      "champ_top_full": {"Spain": 0.27, "Argentina": 0.18}}

def test_compute_aggregates():
    s = ls.compute([E1, E2], latest_champion={"Spain": 0.27, "Argentina": 0.18})
    assert s["documented"] == 2
    assert s["cum_points"] == 4
    assert round(s["mean_brier"], 4) == 0.2828      # (0.1655+0.40)/2
    assert round(s["exact_rate"], 4) == 0.5          # E2 pick == result
    assert s["failure_tally"]["systematic_rating_error"] == 1
    assert s["champ_top"][0] == ["Spain", 0.27]

def test_render_macros_are_consistent():
    s = ls.compute([E1, E2], latest_champion={"Spain": 0.27})
    tex = ls.render_macros(s)
    assert r"\def\liveCumPoints{4}" in tex
    assert r"\def\liveMeanBrier{0.28}" in tex
    assert r"\def\liveDocumented{2}" in tex
