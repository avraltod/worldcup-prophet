"""Tests for fetch_live_inputs.py — all HTTP calls are mocked via injectable opener."""
import json
import sys
from io import BytesIO
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_live_inputs as fli


CLUBELO_CSV = b"""Rank,Club,Country,Level,Elo,From,To
1,Argentina,Argentina,1,1965,2026-06-01,2026-06-30
2,France,France,1,1891,2026-06-01,2026-06-30
3,Spain,Spain,1,1882,2026-06-01,2026-06-30
4,USA,United States,1,1723,2026-06-01,2026-06-30
5,Korea Republic,South Korea,1,1756,2026-06-01,2026-06-30
6,Cote d'Ivoire,Ivory Coast,1,1612,2026-06-01,2026-06-30
99,SomeClub,SomeCountry,2,1400,2026-06-01,2026-06-30
"""


def _opener(csv_bytes):
    class Resp:
        def read(self): return csv_bytes
        def __enter__(self): return self
        def __exit__(self, *a): pass
    return lambda url, timeout=30: Resp()


def test_fetch_clubelo_parses_national_teams():
    result = fli.fetch_clubelo("2026-06-13", opener=_opener(CLUBELO_CSV))
    assert result["Argentina"] == 1965.0
    assert result["France"] == 1891.0


def test_fetch_clubelo_maps_names():
    result = fli.fetch_clubelo("2026-06-13", opener=_opener(CLUBELO_CSV))
    assert "United States" in result       # USA -> United States
    assert "USA" not in result
    assert "South Korea" in result         # Korea Republic -> South Korea
    assert "Korea Republic" not in result
    assert "Ivory Coast" in result         # Cote d'Ivoire -> Ivory Coast


def test_fetch_clubelo_skips_clubs():
    result = fli.fetch_clubelo("2026-06-13", opener=_opener(CLUBELO_CSV))
    assert "SomeClub" not in result        # Level=2 filtered out


def test_clubelo_deltas_vs_june10():
    live_elo = {"Spain": 1882.0, "France": 1900.0}
    import condition as cond
    deltas = fli.compute_elo_deltas(live_elo, cond.ELO)
    spain_d = next(d for d in deltas if d["team"] == "Spain")
    assert spain_d["june10"] == cond.ELO["Spain"]
    assert spain_d["current"] == 1882.0
    assert abs(spain_d["delta"] - (1882.0 - cond.ELO["Spain"])) < 0.01


def test_fetch_clubelo_empty_result_triggers_fallback_in_main(tmp_path, monkeypatch):
    """When ClubElo returns 0 national teams, main() falls back to JUNE10_ELO."""
    import fetch_live_inputs as fli
    import condition as cond
    # Patch fetch_clubelo to return an empty dict (simulating club-only response)
    monkeypatch.setattr(fli, "fetch_clubelo", lambda date_str, opener=None: {})
    monkeypatch.setattr(fli, "OUT_PATH", tmp_path / "live_inputs.json")
    monkeypatch.setattr(fli, "DATA", tmp_path)
    fli.main(["--pre"])
    out = json.loads((tmp_path / "live_inputs.json").read_text())
    # Should fall back to June 10 Elo
    assert len(out["live_elo"]) == len(cond.ELO)
    assert out["source_freshness"]["elo_updated_at"] == "2026-06-10T00:00:00Z"


import condition as cond

# Sample odds API response for Mexico v South Africa (match 1, row 4 in our data)
_MEX_HOME = cond.RATES[4][2]  # "Mexico"
_RSA_AWAY = cond.RATES[4][3]  # "South Africa"

ODDS_API_RESPONSE = json.dumps([{
    "id": "abc123",
    "sport_key": "soccer_fifa_world_cup",
    "home_team": _MEX_HOME,
    "away_team": _RSA_AWAY,
    "bookmakers": [{
        "key": "fanduel",
        "markets": [{
            "key": "h2h",
            "outcomes": [
                {"name": _MEX_HOME,  "price": 1.55},
                {"name": "Draw",     "price": 3.90},
                {"name": _RSA_AWAY,  "price": 6.50},
            ]
        }]
    }]
}]).encode()


def _odds_opener(resp_bytes):
    class Resp:
        def read(self): return resp_bytes
        def __enter__(self): return self
        def __exit__(self, *a): pass
    return lambda req, timeout=30: Resp()


def test_fetch_odds_returns_empty_without_key():
    result = fli.fetch_odds(api_key=None, unplayed_rows=set(),
                            opener=_odds_opener(ODDS_API_RESPONSE))
    assert result == ({}, [])


def test_fetch_odds_maps_fixture_to_row():
    unplayed = {4}  # row 4 = Mexico v South Africa
    rates, details = fli.fetch_odds(
        api_key="TESTKEY", unplayed_rows=unplayed,
        opener=_odds_opener(ODDS_API_RESPONSE))
    assert 4 in rates
    lh, la = rates[4]
    assert lh > la        # Mexico is heavy favorite at these odds


def test_fetch_odds_devig_produces_valid_rates():
    unplayed = {4}
    rates, details = fli.fetch_odds(
        api_key="TESTKEY", unplayed_rows=unplayed,
        opener=_odds_opener(ODDS_API_RESPONSE))
    lh, la = rates[4]
    assert 0.1 <= lh <= 3.4
    assert 0.1 <= la <= 3.4
    assert 1.6 <= lh + la <= 3.4   # within fit_rates total_goals_range


def test_fetch_odds_skips_already_played_rows():
    # Row 4 is played (match 1 already in results), should not appear
    unplayed = set()   # no unplayed rows
    rates, details = fli.fetch_odds(
        api_key="TESTKEY", unplayed_rows=unplayed,
        opener=_odds_opener(ODDS_API_RESPONSE))
    assert 4 not in rates
