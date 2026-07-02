import json
import sys
import datetime as dt
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_results as fr
import live_update_v2 as lu
import market_snapshot


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


def test_parse_scoreboard_surfaces_detail():
    assert fr.parse_scoreboard(_ko_payload("AET"))[0]["detail"] == "AET"
    assert fr.parse_scoreboard(_ko_payload("Pens"))[0]["detail"] == "Pens"
    assert fr.parse_scoreboard(_ko_payload("FT"))[0]["detail"] == "FT"


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


def test_normalize_maps_detail_to_decided():
    aet = lu._normalize(fr.parse_scoreboard(_ko_payload("AET")), _real_log())[0]
    assert aet["decided"] == "et"
    pens = lu._normalize(fr.parse_scoreboard(_ko_payload("Pens")), _real_log())[0]
    assert pens["decided"] == "pens"
    ft = lu._normalize(fr.parse_scoreboard(_ko_payload("FT")), _real_log())[0]
    assert ft["decided"] == "reg"


@pytest.fixture
def light_post(tmp_path, monkeypatch):
    """Isolate make_post_record into tmp and stub the heavy conditioning/market
    calls, so the tests exercise only the result/pending storage logic."""
    monkeypatch.setattr(lu, "TRAJ", tmp_path / "trajectory_v2.json")
    monkeypatch.setattr(lu, "RESULTS", tmp_path / "results_log_v2.json")
    monkeypatch.setattr(lu, "INDEX", tmp_path / "records_index_v2.json")
    (tmp_path / "results_log_v2.json").write_text(json.dumps({"group": {}, "ko": {}}))
    monkeypatch.setattr(lu, "_champion_dist", lambda log: {})
    monkeypatch.setattr(lu, "_champion_dist_b", lambda log: {})
    monkeypatch.setattr(lu, "_info_snapshot", lambda: {})
    monkeypatch.setattr(lu, "_prev_champion", lambda: {})
    monkeypatch.setattr(market_snapshot, "fetch_market_champion", lambda: {})
    return tmp_path


def _post_ev(match, decided, hg, ag, winner="Germany", fh="Germany", fa="Paraguay"):
    return {"match": match, "fh": fh, "fa": fa, "rev": False,
            "kickoff": dt.datetime(2026, 6, 30, 4, 30, tzinfo=dt.timezone.utc),
            "final": True, "has_scores": True, "hg": hg, "ag": ag,
            "event_id": None, "winner": winner, "decided": decided}


def _last(tmp_path):
    return json.loads((tmp_path / "trajectory_v2.json").read_text())[-1]


def test_post_record_holds_reg_score_for_et_ko(light_post):
    now = dt.datetime.now(dt.timezone.utc)
    lu.make_post_record(_post_ev(74, "et", 1, 1), now)      # 1-1 after ET, Germany won
    rec = _last(light_post)
    assert rec["result"] is None
    assert rec["reg_score_pending"] is True
    assert rec["decided"] == "et"
    log = json.loads((light_post / "results_log_v2.json").read_text())
    assert log["ko"]["74"] == "Germany"                     # advancer still recorded


def test_post_record_keeps_reg_score_for_ft_ko(light_post):
    now = dt.datetime.now(dt.timezone.utc)
    lu.make_post_record(_post_ev(74, "reg", 2, 0), now)
    rec = _last(light_post)
    assert rec["result"] == [2, 0]
    assert not rec.get("reg_score_pending")
    assert rec["decided"] == "reg"


def test_post_record_group_game_unchanged(light_post):
    now = dt.datetime.now(dt.timezone.utc)
    ev = _post_ev(1, "reg", 2, 1, winner=None, fh="Mexico", fa="South Africa")
    lu.make_post_record(ev, now)
    rec = _last(light_post)
    assert rec["result"] == [2, 1]
    assert not rec.get("reg_score_pending")


def test_apply_result_writes_ko_winner_not_group():
    log = {"group": {}, "ko": {}}
    lu._apply_result(log, {"match": 74, "hg": 1, "ag": 1, "rev": False, "winner": "Germany"})
    assert log["ko"]["74"] == "Germany" and "74" not in log["group"]
    # a group match still records a scoreline
    lu._apply_result(log, {"match": 1, "hg": 2, "ag": 1, "rev": False, "winner": None})
    assert log["group"]["1"] == [2, 1]
