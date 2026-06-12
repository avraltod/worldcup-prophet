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
