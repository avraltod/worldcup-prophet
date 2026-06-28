import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import update_after_match as uam


def _traj():
    return [
        {"phase": "post", "match": 1, "result": [2, 1]},
        {"phase": "post", "match": 2, "result": [0, 0]},
        {"phase": "post", "match": 73, "winner": "Canada"},   # a knockout result
    ]


def test_pending_matches_excludes_knockouts(tmp_path):
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({"documented": [1]}))
    p = uam.pending_matches(_traj(), idx)
    assert 2 in p          # group edition still pending
    assert 73 not in p     # KO matches are never per-match editions


def test_results_all_includes_group_and_ko():
    r = uam.results_all(_traj())
    assert r["group"]["1"] == [2, 1]
    assert r["group"]["2"] == [0, 0]
    assert r["ko"]["73"] == "Canada"


def test_work_pending_flags_ko_with_no_group_pending(tmp_path, monkeypatch):
    monkeypatch.setattr(uam, "KO_RENDERED", tmp_path / "ko_rendered.json")
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({"documented": [1, 2]}))   # all group docs done
    # only the KO result remains -> there is still work (a living-layer re-render)
    assert uam.work_pending(_traj(), idx) == 1
    # with no KO result and everything documented, there is no work
    grp_only = [r for r in _traj() if r["match"] <= 72]
    assert uam.work_pending(grp_only, idx) == 0


def test_marker_makes_work_pending_idle_until_new_ko(tmp_path, monkeypatch):
    monkeypatch.setattr(uam, "KO_RENDERED", tmp_path / "ko_rendered.json")
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({"documented": [1, 2]}))
    assert uam.work_pending(_traj(), idx) == 1          # M73 not yet incorporated
    uam.mark_ko_incorporated(_traj())
    assert uam.work_pending(_traj(), idx) == 0          # incorporated -> idle
    # a new KO result reopens work
    traj2 = _traj() + [{"phase": "post", "match": 74, "winner": "Germany"}]
    assert uam.work_pending(traj2, idx) == 1
