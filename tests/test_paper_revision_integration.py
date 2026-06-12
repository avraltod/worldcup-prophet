"""Runs the real driver against the committed M1 records into a temp paper tree,
then asserts the living layer updated and the frozen layer did not."""
import json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import update_after_match as uam
import render_evolution as rev


def _synthetic_post_record(pre_record):
    """Build a minimal POST record matching the PRE record's structure."""
    return {
        "phase": "post",
        "match": pre_record["match"],
        "label": pre_record["label"].replace("PRE", "POST"),
        "time": "2026-06-11T22:00:00Z",
        "kickoff": pre_record["kickoff"],
        "n_recorded": 1,
        "champion": pre_record["champion"],
        "market_champion": pre_record["market_champion"],
        "info_bits": 0.05,
        "lineup": None,
        "result": [2, 1],
        "performance": {"points": 3, "brier": 0.25, "p_outcome": 0.67},
    }


def test_opener_revision_updates_living_not_frozen(tmp_path, monkeypatch):
    real_traj = json.loads((ROOT / "data" / "trajectory_v2.json").read_text())
    posts = [r for r in real_traj if r["phase"] == "post"]

    if posts:
        # real POST record exists: use it directly
        traj = real_traj
    else:
        # match not yet played: build a synthetic POST from the real PRE
        pres = [r for r in real_traj if r["phase"] == "pre"]
        if not pres:
            import pytest; pytest.skip("no PRE records in trajectory_v2.json")
        traj = real_traj + [_synthetic_post_record(pres[0])]

    posts = [r for r in traj if r["phase"] == "post"]
    m = posts[0]["match"]

    # write the trajectory (possibly synthetic) to tmp so the driver reads it
    traj_tmp = tmp_path / "trajectory_v2.json"
    traj_tmp.write_text(json.dumps(traj))
    monkeypatch.setattr(uam, "TRAJ_PATH", traj_tmp)

    # redirect the driver's paper paths into tmp
    paper = tmp_path / "paper"; (paper / "match_book").mkdir(parents=True)
    shutil.copy(ROOT / "paper" / "WC2026_paper.tex", paper / "WC2026_paper.tex")
    monkeypatch.setattr(uam, "PAPER", paper)
    monkeypatch.setattr(uam, "INDEX", paper / "match_book" / "index.json")
    monkeypatch.setattr(uam, "CORRECTIONS", paper / "match_book" / "corrections.md")
    monkeypatch.setattr(uam, "REVISIONS", paper / "REVISIONS.md")
    monkeypatch.setattr(uam, "PAPER_TEX", paper / "WC2026_paper.tex")
    monkeypatch.setattr(uam, "LIVE_STATS_TEX", paper / "live_stats.tex")

    frozen_before = rev.frozen_hash((paper / "WC2026_paper.tex").read_text())
    stats = uam.revise(m, use_api=False)
    tex_after = (paper / "WC2026_paper.tex").read_text()

    assert stats["documented"] == 1
    assert (paper / "match_book" / f"M{m:03d}.md").exists()
    assert (paper / "live_stats.tex").exists()
    assert "LIVE-EVOLUTION-TABLE:START" in tex_after
    assert rev.frozen_hash(tex_after) == frozen_before     # frozen layer untouched
