"""End-to-end publish-path test: fake ESPN fetch -> real record_update + score_day
-> README render. Restores all mutated files in teardown so the repo is untouched.
This is the test that would have caught the missing experiment/ directory."""
import sys, json, datetime as dt, shutil
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import live_update as lu
import fetch_results as fr

RESULTS_LOG = ROOT / "data" / "results_log.json"
TRAJ = ROOT / "data" / "trajectory.json"
README = ROOT / "README.md"
EXPERIMENT = ROOT / "experiment"
LEDGER = EXPERIMENT / "ledger.csv"


@pytest.fixture
def restore_repo():
    # snapshot EVERY file the publish path mutates — including the ledger,
    # which holds real tournament rows the test must never destroy. Bytes,
    # not text: the csv module writes CRLF and read_text would normalize it.
    saved = {}
    for p in (RESULTS_LOG, TRAJ, README, LEDGER):
        saved[p] = p.read_bytes() if p.exists() else None
    experiment_existed = EXPERIMENT.exists()
    yield
    # restore files (delete any the test created that did not exist before)
    for p, data in saved.items():
        if data is None:
            if p.exists():
                p.unlink()
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
    # remove experiment/ entirely only if the test created it
    if not experiment_existed and EXPERIMENT.exists():
        shutil.rmtree(EXPERIMENT)


def test_full_publish_creates_ledger_and_updates_readme(restore_repo, monkeypatch):
    # ensure a clean slate for match 4 (Mexico v South Africa)
    RESULTS_LOG.write_text(json.dumps({"group": {}, "ko": {}}))
    # if experiment/ledger.csv exists from a prior real run, remove so we test creation
    if LEDGER.exists():
        LEDGER.unlink()

    long_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=6)
    fake = [{"home": "Mexico", "away": "South Africa", "hg": 2, "ag": 1,
             "kickoff": long_ago, "final": True}]
    monkeypatch.setattr(fr, "fetch_dates", lambda dates: fake)

    rc = lu.main([])  # real record_update.py + score_day.py + README render
    assert rc == 0

    log = json.loads(RESULTS_LOG.read_text())
    assert log["group"].get("1") == [2, 1]
    assert LEDGER.exists(), "experiment/ledger.csv must be created even if experiment/ was absent"
    readme = README.read_text()
    assert "M1:" in readme and "Mexico" in readme
