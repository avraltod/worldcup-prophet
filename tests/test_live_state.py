"""learning_state_2026: init from condition's Elo+adj, idempotent apply, queue."""
import json

import live_state as lst


def _stats(sot_h=6, sot_a=2):
    return {"home": {"team": "H", "sot": sot_h, "other_shots": 4,
                     "total_shots": sot_h + 4, "possession": 55.0},
            "away": {"team": "A", "sot": sot_a, "other_shots": 3,
                     "total_shots": sot_a + 3, "possession": 45.0}}


def test_baseline_covers_all_elo_teams():
    base = lst.baseline_2026()
    assert "Spain" in base and "Mexico" in base
    import condition as cond
    assert base["Portugal"] == cond.ELO["Portugal"] + cond.ADJ.get("Portugal", 0)


def test_state_roundtrip_and_apply(tmp_path, monkeypatch):
    monkeypatch.setattr(lst, "STATE_PATH", tmp_path / "state.json")
    st = lst.load_state()
    assert st["processed"] == [] and st["pending"] == []
    st, rec = lst.apply_match(st, 1, "Mexico", "South Africa", _stats())
    assert rec["match"] == 1
    assert "home" in rec["lam_obs"] and "home" in rec["lam_exp"]
    assert st["drift"].get("Mexico", 0) != 0
    lst.save_state(st)
    st2 = lst.load_state()
    assert st2["drift"] == st["drift"]


def test_apply_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(lst, "STATE_PATH", tmp_path / "state.json")
    st = lst.load_state()
    st, _ = lst.apply_match(st, 1, "Mexico", "South Africa", _stats())
    drift_once = dict(st["drift"])
    st, rec2 = lst.apply_match(st, 1, "Mexico", "South Africa", _stats())
    assert rec2 is None and st["drift"] == drift_once


def test_sync_queues_missing_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(lst, "STATE_PATH", tmp_path / "state.json")
    st = lst.load_state()
    entries = [{"match": 1, "fixture": "Mexico v South Africa"},
               {"match": 2, "fixture": "South Korea v Czechia"}]
    st = lst.sync(st, entries, lambda m: _stats() if m == 1 else None)
    assert [r["match"] for r in st["processed"]] == [1]
    assert st["pending"] == [2]
    # stats arrive later: sync drains the queue
    st = lst.sync(st, entries, lambda m: _stats())
    assert [r["match"] for r in st["processed"]] == [1, 2]
    assert st["pending"] == []


def test_ratings_are_baseline_plus_drift(tmp_path, monkeypatch):
    monkeypatch.setattr(lst, "STATE_PATH", tmp_path / "state.json")
    st = lst.load_state()
    st, _ = lst.apply_match(st, 1, "Mexico", "South Africa", _stats())
    r = lst.ratings(st)
    assert r["Mexico"] == st["baseline"]["Mexico"] + st["drift"]["Mexico"]
    assert r["Spain"] == st["baseline"]["Spain"]


import json as _json


def test_load_live_inputs_returns_empty_when_file_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(lst, "ROOT", tmp_path)
    assert lst.load_live_inputs() == {}


def test_load_live_inputs_returns_data_when_present(tmp_path, monkeypatch):
    monkeypatch.setattr(lst, "ROOT", tmp_path)
    (tmp_path / "data").mkdir()
    data = {"fetched_at": "2026-06-13T12:00:00Z", "live_elo": {"Spain": 1900.0}}
    (tmp_path / "data" / "live_inputs.json").write_text(_json.dumps(data))
    result = lst.load_live_inputs()
    assert result["live_elo"]["Spain"] == 1900.0


def test_build_eff_elo_no_live_data_matches_june10_plus_host_plus_drift(tmp_path, monkeypatch):
    import condition as cond
    monkeypatch.setattr(lst, "STATE_PATH", tmp_path / "state.json")
    state = lst.load_state()
    state["drift"] = {"Mexico": -49.94}
    eff = lst.build_eff_elo(state, {})
    # Mexico is a host: ELO + ADJ + host(60) + drift
    expected = cond.ELO["Mexico"] + cond.ADJ.get("Mexico", 0) + 60 + (-49.94)
    assert abs(eff["Mexico"] - expected) < 0.01
    # Non-host non-drift team: ELO + ADJ
    expected_spain = cond.ELO["Spain"] + cond.ADJ.get("Spain", 0)
    assert abs(eff["Spain"] - expected_spain) < 0.01


def test_build_eff_elo_uses_live_elo_when_provided(tmp_path, monkeypatch):
    monkeypatch.setattr(lst, "STATE_PATH", tmp_path / "state.json")
    state = lst.load_state()
    live = {"live_elo": {"Spain": 1999.0}, "live_injury_adj": {}, "lineup_adj": {}}
    eff = lst.build_eff_elo(state, live)
    # Spain is not a host; no adj, no drift
    assert abs(eff["Spain"] - 1999.0) < 0.01


def test_build_eff_elo_applies_live_injury_adj(tmp_path, monkeypatch):
    import condition as cond
    monkeypatch.setattr(lst, "STATE_PATH", tmp_path / "state.json")
    state = lst.load_state()
    live = {"live_injury_adj": {"Brazil": -35}}
    eff = lst.build_eff_elo(state, live)
    expected = cond.ELO["Brazil"] + (-35)
    assert abs(eff["Brazil"] - expected) < 0.01


def test_build_eff_elo_applies_lineup_adj(tmp_path, monkeypatch):
    import condition as cond
    monkeypatch.setattr(lst, "STATE_PATH", tmp_path / "state.json")
    state = lst.load_state()
    live_no_lineup = {}
    live_with_lineup = {"lineup_adj": {"France": -20}}
    eff_base = lst.build_eff_elo(state, live_no_lineup)
    eff_adj = lst.build_eff_elo(state, live_with_lineup)
    assert abs(eff_adj["France"] - eff_base["France"] - (-20)) < 0.01
