import sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import live_update_v2 as v2

NOW = dt.datetime(2026, 6, 11, 18, 30, tzinfo=dt.timezone.utc)

def ev(match, mins_to_kickoff, final=False, has_scores=False):
    return {"match": match, "kickoff": NOW + dt.timedelta(minutes=mins_to_kickoff),
            "final": final, "has_scores": has_scores}

EMPTY = {"pre": [], "post": []}

def test_pre_fires_in_window_once():
    assert v2.plan_records([ev(1, 30)], EMPTY, NOW) == [(1, "pre")]

def test_pre_not_fired_outside_window():
    assert v2.plan_records([ev(1, 200)], EMPTY, NOW) == []
    assert v2.plan_records([ev(1, -10)], EMPTY, NOW) == []

def test_pre_skipped_if_already_done():
    assert v2.plan_records([ev(1, 30)], {"pre": [1], "post": []}, NOW) == []

def test_post_fires_when_final_once():
    assert v2.plan_records([ev(1, -120, final=True, has_scores=True)], EMPTY, NOW) == [(1, "post")]

def test_post_skipped_if_recorded_or_not_final():
    assert v2.plan_records([ev(1, -120, final=True, has_scores=True)],
                           {"pre": [], "post": [1]}, NOW) == []
    assert v2.plan_records([ev(1, -120, final=False, has_scores=False)], EMPTY, NOW) == []

def test_md3_two_simultaneous_yield_two_pre_in_match_order():
    assert v2.plan_records([ev(8, 30), ev(7, 30)], EMPTY, NOW) == [(7, "pre"), (8, "pre")]


import json as _json
from pathlib import Path
import live_state as lst
import live_update_v2 as v2


def test_champion_dist_b_returns_empty_without_live_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(lst, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(lst, "ROOT", tmp_path)
    (tmp_path / "data").mkdir()
    results = {"group": {}, "ko": {}}
    dist = v2._champion_dist_b(results)
    assert dist == {}


def test_champion_dist_b_returns_distribution_with_live_elo(tmp_path, monkeypatch):
    monkeypatch.setattr(lst, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(lst, "ROOT", tmp_path)
    (tmp_path / "data").mkdir()
    import condition as cond
    live_data = {"live_elo": {t: cond.ELO[t] for t in cond.ELO},
                 "live_injury_adj": {}, "lineup_adj": {}}
    (tmp_path / "data" / "live_inputs.json").write_text(_json.dumps(live_data))
    results = {"group": {}, "ko": {}}
    dist = v2._champion_dist_b(results)
    assert len(dist) > 0
    assert all(0 <= v <= 1 for v in dist.values())


def test_info_snapshot_returns_summary_and_freshness(tmp_path, monkeypatch):
    monkeypatch.setattr(lst, "ROOT", tmp_path)
    (tmp_path / "data").mkdir()
    live_data = {
        "fetched_at": "2026-06-13T12:00:00Z",
        "source_freshness": {"elo_updated_at": "2026-06-13T08:00:00Z"},
        "deltas": {"summary": {"elo_rms_delta": 15.2, "n_rate_changes": 0}},
    }
    (tmp_path / "data" / "live_inputs.json").write_text(_json.dumps(live_data))
    snap = v2._info_snapshot()
    assert snap["fetched_at"] == "2026-06-13T12:00:00Z"
    assert snap["elo_rms_delta"] == 15.2


def test_info_snapshot_returns_empty_without_live_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(lst, "ROOT", tmp_path)
    snap = v2._info_snapshot()
    assert snap == {}
