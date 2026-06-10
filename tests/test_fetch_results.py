import sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_results as fr

SAMPLE = {"events": [
    {"date": "2026-06-11T19:00Z", "competitions": [{
        "status": {"type": {"state": "post", "completed": True, "detail": "FT"}},
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "Mexico"}, "score": "2"},
            {"homeAway": "away", "team": {"displayName": "South Africa"}, "score": "1"}]}]},
    {"date": "2026-06-12T02:00Z", "competitions": [{
        "status": {"type": {"state": "in", "completed": False, "detail": "2nd Half"}},
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "South Korea"}, "score": "0"},
            {"homeAway": "away", "team": {"displayName": "Czechia"}, "score": "0"}]}]},
]}

def test_parse_extracts_score_and_finality():
    rows = fr.parse_scoreboard(SAMPLE)
    assert len(rows) == 2
    m = rows[0]
    assert m["home"] == "Mexico" and m["away"] == "South Africa"
    assert m["hg"] == 2 and m["ag"] == 1
    assert m["final"] is True
    assert m["kickoff"] == dt.datetime(2026, 6, 11, 19, 0, tzinfo=dt.timezone.utc)
    assert rows[1]["final"] is False

def test_map_to_fixture_matches_and_orients():
    # Mexico v South Africa is the opener = OFFICIAL match number 1 (sheet row 4)
    assert fr.map_to_fixture("Mexico", "South Africa")[0] == 1
    r, fh, fa, rev = fr.map_to_fixture("South Africa", "Mexico")
    assert r == 1 and fh == "Mexico" and fa == "South Africa" and rev is True
    assert fr.map_to_fixture("Mars", "Venus") is None

def test_parse_includes_event_id():
    payload = {"events": [{"id": "633850", "date": "2026-06-11T19:00Z",
        "competitions": [{
            "status": {"type": {"state": "post", "completed": True, "detail": "FT"}},
            "competitors": [
                {"homeAway": "home", "team": {"displayName": "Mexico"}, "score": "2"},
                {"homeAway": "away", "team": {"displayName": "South Africa"}, "score": "1"}]}]}]}
    assert fr.parse_scoreboard(payload)[0]["event_id"] == "633850"
