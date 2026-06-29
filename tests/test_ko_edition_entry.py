import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ko_edition as ke

def _records(match, pre=True):
    post = {"phase": "post", "match": match, "result": [0, 1], "winner": "Canada",
            "champion": {"France": 0.27}, "champion_b": {"France": 0.3},
            "info_bits": 0.012, "kickoff": "2026-06-28T19:00:00Z"}
    recs = [post]
    if pre:
        recs.insert(0, {"phase": "pre", "match": match, "champion": {"France": 0.26},
                        "champion_b": {"France": 0.29}, "market_champion": {"France": 0.25},
                        "kickoff": "2026-06-28T19:00:00Z"})
    return recs

def test_entry_scores_frozen2_and_contrasts_frozen1():
    f2 = json.loads((ROOT / "data" / "frozen2_entry.json").read_text())["picks"]
    e = ke.build_ko_entry(73, _records(73), f2, actual_home="South Africa",
                          actual_away="Canada")
    assert e["match"] == 73
    assert e["advancer"] == "Canada" and e["frozen2_hit"] is True  # F2 picked Canada
    assert isinstance(e["frozen2_points"], int)
    assert "frozen1_points" in e and "recond_delta" in e  # F2 - F1
    assert e["info_bits"] == 0.012

def test_post_only_when_no_pre_record():
    f2 = json.loads((ROOT / "data" / "frozen2_entry.json").read_text())["picks"]
    e = ke.build_ko_entry(73, _records(73, pre=False), f2,
                          actual_home="South Africa", actual_away="Canada")
    assert e["pre"] is None and e["post_only"] is True
