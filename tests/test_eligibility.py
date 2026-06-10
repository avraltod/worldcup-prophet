import sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_results as fr

NOW = dt.datetime(2026, 6, 12, 13, 0, tzinfo=dt.timezone.utc)

def row(home, away, hg, ag, kickoff, final):
    return {"home": home, "away": away, "hg": hg, "ag": ag,
            "kickoff": kickoff, "final": final}

def t(h):
    return NOW - dt.timedelta(hours=h)

def test_clean_matured_final_match_becomes_target():
    parsed = [row("Mexico", "South Africa", 2, 1, t(6), True)]
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {}, "ko": {}}, NOW)
    assert holds == []
    assert targets == {"4": [2, 1]}
    assert scored == [{"home": "Mexico", "away": "South Africa", "hg": 2, "ag": 1}]

def test_reversed_orientation_is_normalized_to_fixture():
    parsed = [row("South Africa", "Mexico", 1, 2, t(6), True)]
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {}, "ko": {}}, NOW)
    assert targets == {"4": [2, 1]} and holds == []

def test_matured_but_not_final_holds_the_day():
    parsed = [row("Mexico", "South Africa", 1, 1, t(6), False)]
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {}, "ko": {}}, NOW)
    assert targets == {} and len(holds) == 1 and "not FT" in holds[0]

def test_unmatured_match_is_silently_excluded():
    parsed = [row("Mexico", "South Africa", 0, 0, t(1), False)]
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {}, "ko": {}}, NOW)
    assert targets == {} and holds == []

def test_already_recorded_match_is_skipped():
    parsed = [row("Mexico", "South Africa", 2, 1, t(6), True)]
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {"4": [2, 1]}, "ko": {}}, NOW)
    assert targets == {} and holds == []

def test_score_out_of_bounds_holds():
    parsed = [row("Mexico", "South Africa", 99, 1, t(6), True)]
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {}, "ko": {}}, NOW)
    assert targets == {} and len(holds) == 1 and "out of bounds" in holds[0]

def test_non_group_event_ignored():
    parsed = [row("Mars", "Venus", 1, 0, t(6), True)]
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {}, "ko": {}}, NOW)
    assert targets == {} and holds == []
