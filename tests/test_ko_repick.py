import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ko_repick as kr
import condition as C


def _predicted_results():
    pr = json.loads((ROOT / "data" / "predictions_realistic.json").read_text())
    groups = {str(p["num"]): [p["hg"], p["ag"]]
              for p in pr if str(p["stage"]).startswith("Group")}
    return {"group": groups, "ko": {}}


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
