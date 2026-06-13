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
