"""Runs the real driver against the committed records into a temp paper tree,
then asserts every living unit rendered and the skeleton stayed byte-identical."""
import hashlib, json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import update_after_match as uam
import live_state as lst
import vintages as vin
import fetch_stats_espn as fse

EXPECTED_UNITS = ["stats", "champ_table", "trajfig", "ledger", "narrative",
                  "divergence", "revision_report", "tracker", "two_track",
                  "survival_colcomp"] + [f"group_{g}" for g in "ABCDEFGHIJKL"]


def _setup(tmp_path, monkeypatch):
    """Sandbox every driver path global; returns (paper_dir, first_post_match)."""
    real_traj = json.loads((ROOT / "data" / "trajectory_v2.json").read_text())
    posts = [r for r in real_traj if r["phase"] == "post"]
    if not posts:
        import pytest; pytest.skip("no POST records yet")
    m = posts[0]["match"]

    traj_tmp = tmp_path / "trajectory_v2.json"
    traj_tmp.write_text(json.dumps(real_traj))
    monkeypatch.setattr(uam, "TRAJ_PATH", traj_tmp)

    paper = tmp_path / "paper"; (paper / "match_book").mkdir(parents=True)
    shutil.copy(ROOT / "paper" / "WC2026_paper.tex", paper / "WC2026_paper.tex")
    monkeypatch.setattr(uam, "PAPER", paper)
    monkeypatch.setattr(uam, "INDEX", paper / "match_book" / "index.json")
    monkeypatch.setattr(uam, "CORRECTIONS", paper / "match_book" / "corrections.md")
    monkeypatch.setattr(uam, "REVISIONS", paper / "REVISIONS.md")
    monkeypatch.setattr(uam, "PAPER_TEX", paper / "WC2026_paper.tex")
    monkeypatch.setattr(uam, "LIVE_DIR", paper / "live")
    monkeypatch.setattr(uam, "SKELETON_SHA", tmp_path / "skeleton_sha256.txt")
    (tmp_path / "skeleton_sha256.txt").write_text(
        hashlib.sha256((paper / "WC2026_paper.tex").read_bytes()).hexdigest())
    monkeypatch.setattr(lst, "STATE_PATH", tmp_path / "learning_state.json")
    monkeypatch.setattr(vin, "PATH", tmp_path / "vintages.json")
    monkeypatch.setattr(fse, "STATS_DIR", tmp_path / "match_stats")
    monkeypatch.setattr(uam, "COND_N", 400)      # keep the test fast
    monkeypatch.setattr(uam, "TWO_TRACK_N", 200)
    return paper, m


def test_revision_renders_every_unit_and_skeleton_is_untouched(tmp_path, monkeypatch):
    paper, m = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(fse, "get_stats", lambda match, kickoff: None)  # offline

    skeleton_before = (paper / "WC2026_paper.tex").read_bytes()
    stats = uam.revise(m, use_api=False)

    assert (paper / "WC2026_paper.tex").read_bytes() == skeleton_before
    for unit in EXPECTED_UNITS:
        f = paper / "live" / f"{unit}.tex"
        assert f.exists(), f"missing living unit {unit}"
    assert stats["documented"] >= 1
    rows = json.loads((tmp_path / "vintages.json").read_text())
    assert rows[-1]["edition"] == m
    state = json.loads((tmp_path / "learning_state.json").read_text())
    assert m in state["pending"]                  # stats were offline -> queued


def test_revision_with_box_score_runs_the_two_track(tmp_path, monkeypatch):
    """The with-stats seam: sync -> two-track re-simulation -> history ->
    performance release -> implications, end to end through the driver."""
    paper, m = _setup(tmp_path, monkeypatch)
    fake = {"home": {"team": "Home", "sot": 5.0, "other_shots": 6.0,
                     "total_shots": 11.0, "possession": 58.0},
            "away": {"team": "Away", "sot": 1.0, "other_shots": 2.0,
                     "total_shots": 3.0, "possession": 42.0}}
    monkeypatch.setattr(fse, "get_stats", lambda match, kickoff: fake)

    uam.revise(m, use_api=False)

    state = json.loads((tmp_path / "learning_state.json").read_text())
    assert [r["match"] for r in state["processed"]] == [m]
    assert state["pending"] == []
    assert state["history"] and state["history"][-1]["match"] == m
    assert state["drift"]                          # the update actually moved ratings

    two = (paper / "live" / "two_track.tex").read_text()
    assert "Frozen" in two and "Track~B" in two and "Drift" in two
    rr = (paper / "live" / "revision_report.tex").read_text()
    assert "Shots" in rr                           # box-score table rendered
    assert "lambda" in rr                          # performance vs expectation line
    assert "Implications" in rr                    # remaining-fixture odds present
