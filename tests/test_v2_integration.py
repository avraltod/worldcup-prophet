"""End-to-end v2: a pre record (snapshot, no result applied) then a post record (result
applied + performance), using real conditioning. Restores v2 files in teardown.
Uses M1's actual locked pick so the post is an exact hit (3 points)."""
import sys, json, datetime as dt
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import live_update_v2 as v2

TRAJ = ROOT / "data" / "trajectory_v2.json"
RESULTS = ROOT / "data" / "results_log_v2.json"
INDEX = ROOT / "data" / "records_index_v2.json"
PICK = next(m for m in json.loads((ROOT / "data" / "match_expectations.json").read_text())
            if m["match"] == 1)["pick"]


@pytest.fixture
def clean_v2():
    saved = {p: (p.read_text() if p.exists() else None) for p in (TRAJ, RESULTS, INDEX)}
    for p in (TRAJ, RESULTS, INDEX):
        p.exists() and p.unlink()
    yield
    for p, text in saved.items():
        if text is None:
            p.exists() and p.unlink()
        else:
            p.write_text(text)


def _ev(match):
    return {"match": match, "fh": "Mexico", "fa": "South Africa", "rev": False,
            "kickoff": dt.datetime(2026, 6, 11, 19, 0, tzinfo=dt.timezone.utc),
            "final": True, "has_scores": True, "hg": PICK[0], "ag": PICK[1], "event_id": None}


def test_pre_then_post_records(clean_v2):
    RESULTS.write_text(json.dumps({"group": {}, "ko": {}}))
    now = dt.datetime.now(dt.timezone.utc)

    v2.make_pre_record(_ev(1), now)
    traj = json.loads(TRAJ.read_text())
    assert traj[-1]["phase"] == "pre" and traj[-1]["match"] == 1
    assert traj[-1]["result"] is None and traj[-1]["champion"]       # forecast present
    assert json.loads(RESULTS.read_text())["group"] == {}            # pre applies no result

    v2.make_post_record(_ev(1), now)
    traj = json.loads(TRAJ.read_text())
    assert traj[-1]["phase"] == "post" and traj[-1]["result"] == [PICK[0], PICK[1]]
    assert traj[-1]["performance"]["points"] == 3                    # exact pick -> 3 pts
    assert json.loads(RESULTS.read_text())["group"]["1"] == [PICK[0], PICK[1]]
    assert json.loads(INDEX.read_text()) == {"pre": [1], "post": [1]}


def test_append_is_deduped_on_phase_match(clean_v2):
    # crash-safety: re-recording the same (phase, match) must not duplicate the entry
    RESULTS.write_text(json.dumps({"group": {}, "ko": {}}))
    now = dt.datetime.now(dt.timezone.utc)
    v2.make_pre_record(_ev(1), now)
    v2.make_pre_record(_ev(1), now)        # retry after a hypothetical crash before _mark
    traj = json.loads(TRAJ.read_text())
    assert sum(1 for r in traj if r["phase"] == "pre" and r["match"] == 1) == 1
