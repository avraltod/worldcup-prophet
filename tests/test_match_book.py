import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import match_book as mb

PRE = {"phase": "pre", "match": 1, "kickoff": "2026-06-11T19:00:00Z",
       "champion": {"Spain": 0.2711, "Argentina": 0.1768, "France": 0.1428,
                    "Portugal": 0.093, "England": 0.0698, "Brazil": 0.0359},
       "market_champion": {"Spain": 0.164, "France": 0.155, "Portugal": 0.106},
       "info_bits": 0.0, "result": None, "performance": None}
POST = {"phase": "post", "match": 1, "kickoff": "2026-06-11T19:00:00Z",
        "champion": {"Spain": 0.2711, "Argentina": 0.1815, "England": 0.0688},
        "info_bits": 0.0011, "result": [2, 0],
        "performance": {"points": 1, "ev_points": 0.855, "p_outcome": 0.6718, "brier": 0.1655}}
EXP = [{"match": 1, "group": "A", "home": "Mexico", "away": "South Africa",
        "pick": [2, 1], "probs_HDA": [0.6718, 0.2087, 0.1193], "lh": 1.9, "la": 0.65}]

def test_build_entry_fills_pre_and_post_from_records():
    e = mb.build_entry(1, [PRE, POST], EXP, forecast_commit="abc1234",
                       documented_at="2026-06-11T21:10:58Z")
    assert e["match"] == 1
    assert e["stage"] == "Group A"
    assert e["fixture"] == "Mexico v South Africa"
    assert e["result"] == [2, 0]
    assert e["pre"]["pick"] == [2, 1]
    assert e["pre"]["champ_top"][0] == ["Spain", 0.2711]
    assert e["post"]["points"] == 1
    assert e["post"]["brier"] == 0.1655
    assert ["Argentina", 0.1768, 0.1815] in e["post"]["movers"]
    assert e["interpretation"] == ""
    assert e["forecast_commit"] == "abc1234"

def test_roundtrip_markdown():
    e = mb.build_entry(1, [PRE, POST], EXP, "abc1234", "2026-06-11T21:10:58Z")
    e["interpretation"] = "A likely home win arrived; the title race barely moved."
    e["interpretation_source"] = "human"
    e["failure_mode"] = None
    text = mb.to_markdown(e)
    back = mb.parse_markdown(text)
    assert back["match"] == 1
    assert back["interpretation"] == e["interpretation"]
    assert back["interpretation_source"] == "human"
    assert back["pre"]["pick"] == [2, 1]
    assert back["result"] == [2, 0]

def test_index_mark_and_query(tmp_path):
    idx = tmp_path / "index.json"
    assert mb.is_documented(idx, 1) is False
    mb.mark_documented(idx, 1)
    assert mb.is_documented(idx, 1) is True
    assert mb.documented_matches(idx) == [1]
