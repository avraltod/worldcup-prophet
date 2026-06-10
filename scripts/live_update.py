"""Daily live-update orchestrator (group stage).

Fetch ESPN scores -> gate -> (if clean & new) run record_update.py + score_day.py
-> re-render the README LIVE-RESULTS block. Writes ONLY the allowlisted files.
Exit codes: 0 = published or nothing-to-do; 1 = HOLD (alert). Use --dry-run to
print the decision without writing anything."""
import datetime as dt
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import fetch_results as fr
import render_readme as rr

RESULTS_LOG = ROOT / "data" / "results_log.json"
TRAJ = ROOT / "data" / "trajectory.json"
README = ROOT / "README.md"


@dataclass
class Decision:
    exit_code: int
    targets: dict = field(default_factory=dict)
    scored: list = field(default_factory=list)
    holds: list = field(default_factory=list)


def decide(parsed, results_log, now_utc):
    """Pure decision: parsed ESPN rows + current log -> Decision."""
    targets, holds, scored = fr.eligible_targets(parsed, results_log, now_utc)
    if holds:
        return Decision(exit_code=1, holds=holds)
    if not targets:
        return Decision(exit_code=0)
    return Decision(exit_code=0, targets=targets, scored=scored)


def _date_window(now_utc, back_days=3):
    """YYYYMMDD strings to query: covers UTC-boundary + a few missed runs."""
    return [(now_utc.date() - dt.timedelta(days=i)).strftime("%Y%m%d")
            for i in range(back_days + 1)]


def main(argv):
    dry = "--dry-run" in argv
    now = dt.datetime.now(dt.timezone.utc)
    parsed = fr.fetch_dates(_date_window(now))
    log = json.loads(RESULTS_LOG.read_text())
    decision = decide(parsed, log, now)

    if decision.holds:
        for h in decision.holds:
            print(f"HOLD: {h}", file=sys.stderr)
        return 1
    if not decision.targets:
        print("No new matured group matches; nothing to publish.")
        return 0

    print(f"Publishing {len(decision.targets)} match(es): {sorted(decision.targets)}")
    if dry:
        print("--dry-run: no files written.")
        return 0

    label = now.date().isoformat()
    subprocess.run([sys.executable, str(HERE / "record_update.py"),
                    json.dumps({"group": decision.targets}), label],
                   check=True, cwd=ROOT)
    subprocess.run([sys.executable, str(HERE / "score_day.py"),
                    json.dumps(decision.scored)], check=True, cwd=ROOT)

    trajectory = json.loads(TRAJ.read_text())
    log_after = json.loads(RESULTS_LOG.read_text())
    block = rr.render_results_block(trajectory, log_after)
    README.write_text(rr.replace_readme_block(README.read_text(), block))
    print("README results block updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
