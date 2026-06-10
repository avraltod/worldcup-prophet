import sys, json, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import live_update as lu

NOW = dt.datetime(2026, 6, 12, 13, 0, tzinfo=dt.timezone.utc)

def parsed_one(final=True, hours=6):
    return [{"home": "Mexico", "away": "South Africa", "hg": 2, "ag": 1,
             "kickoff": NOW - dt.timedelta(hours=hours), "final": final}]

def test_plan_holds_returns_exit_1(tmp_path):
    log = {"group": {}, "ko": {}}
    decision = lu.decide(parsed_one(final=False), log, NOW)
    assert decision.exit_code == 1 and decision.targets == {}
    assert any("not FT" in h for h in decision.holds)

def test_plan_noop_returns_exit_0(tmp_path):
    log = {"group": {"1": [2, 1]}, "ko": {}}
    decision = lu.decide(parsed_one(), log, NOW)
    assert decision.exit_code == 0 and decision.targets == {}

def test_plan_clean_returns_targets_exit_0():
    decision = lu.decide(parsed_one(), {"group": {}, "ko": {}}, NOW)
    assert decision.exit_code == 0 and decision.targets == {"1": [2, 1]}
    assert decision.scored[0]["home"] == "Mexico"
