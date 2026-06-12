"""parse_summary: ESPN summary JSON -> {'home': {...}, 'away': {...}} or None."""
import json
from pathlib import Path

import fetch_stats_espn as fse

FIXTURE = Path(__file__).parent / "fixtures" / "espn_summary_M001.json"


def test_parse_summary_real_payload():
    parsed = fse.parse_summary(json.loads(FIXTURE.read_text()))
    assert set(parsed) == {"home", "away"}
    for side in ("home", "away"):
        s = parsed[side]
        assert isinstance(s["sot"], (int, float)) and s["sot"] >= 0
        assert isinstance(s["other_shots"], (int, float)) and s["other_shots"] >= 0
        assert s["total_shots"] == s["sot"] + s["other_shots"]
        assert s["team"]


def test_parse_summary_missing_stats_returns_none():
    payload = json.loads(FIXTURE.read_text())
    for t in payload["boxscore"]["teams"]:
        t["statistics"] = [s for s in t["statistics"]
                           if s.get("name") not in fse._SOT_KEYS]
    assert fse.parse_summary(payload) is None


def test_get_stats_uses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(fse, "STATS_DIR", tmp_path)
    cached = {"match": 1, "event_id": "x",
              "stats": {"home": {"team": "Mexico", "sot": 5, "other_shots": 7,
                                 "total_shots": 12, "possession": 60.0},
                        "away": {"team": "South Africa", "sot": 1, "other_shots": 3,
                                 "total_shots": 4, "possession": 40.0}}}
    (tmp_path / "M001.json").write_text(json.dumps(cached))

    def boom(*a, **k):
        raise AssertionError("network must not be touched on cache hit")
    monkeypatch.setattr(fse, "_fetch_json", boom)
    assert fse.get_stats(1, "2026-06-11T19:00:00Z") == cached["stats"]
