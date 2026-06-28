import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_results as fr
import live_update_v2 as lu


def _real_log():
    return json.loads((ROOT / "data" / "results_log_v2.json").read_text())


def _ko_payload(detail="AET"):
    # a completed knockout game decided after extra time; Germany advances
    return {"events": [{"id": "e74", "date": "2026-06-30T04:30:00Z",
        "competitions": [{
            "status": {"type": {"state": "post", "completed": True, "detail": detail}},
            "competitors": [
                {"homeAway": "home", "team": {"displayName": "Germany"}, "score": "1", "winner": True},
                {"homeAway": "away", "team": {"displayName": "Paraguay"}, "score": "1", "winner": False},
            ]}]}]}


def test_parse_scoreboard_extracts_winner_and_completed():
    p = fr.parse_scoreboard(_ko_payload())[0]
    assert p["winner"] == "Germany"
    assert p["completed"] is True
    assert p["final"] is False          # detail != FT, so the group 'final' gate stays off


def test_ko_fixture_maps_real_matchup():
    fx = fr.ko_fixture("Germany", "Paraguay", _real_log())
    assert fx is not None
    assert fx[0] == 74                  # match number of Germany v Paraguay


def test_ko_fixture_none_for_unknown_pair():
    assert fr.ko_fixture("Germany", "Brazil", _real_log()) is None   # not a real KO matchup


def test_normalize_maps_ko_event_and_carries_winner():
    parsed = fr.parse_scoreboard(_ko_payload())
    events = lu._normalize(parsed, _real_log())
    assert len(events) == 1
    e = events[0]
    assert e["match"] == 74 and e["is_ko"] is True
    assert e["winner"] == "Germany"
    assert e["final"] is True           # KO final = completed AND a winner is known


def test_apply_result_writes_ko_winner_not_group():
    log = {"group": {}, "ko": {}}
    lu._apply_result(log, {"match": 74, "hg": 1, "ag": 1, "rev": False, "winner": "Germany"})
    assert log["ko"]["74"] == "Germany" and "74" not in log["group"]
    # a group match still records a scoreline
    lu._apply_result(log, {"match": 1, "hg": 2, "ag": 1, "rev": False, "winner": None})
    assert log["group"]["1"] == [2, 1]
