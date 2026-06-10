import sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import live_update_v2 as v2

NOW = dt.datetime(2026, 6, 11, 18, 30, tzinfo=dt.timezone.utc)

def ev(match, mins_to_kickoff, final=False, has_scores=False):
    return {"match": match, "kickoff": NOW + dt.timedelta(minutes=mins_to_kickoff),
            "final": final, "has_scores": has_scores}

EMPTY = {"pre": [], "post": []}

def test_pre_fires_in_window_once():
    assert v2.plan_records([ev(1, 30)], EMPTY, NOW) == [(1, "pre")]

def test_pre_not_fired_outside_window():
    assert v2.plan_records([ev(1, 200)], EMPTY, NOW) == []
    assert v2.plan_records([ev(1, -10)], EMPTY, NOW) == []

def test_pre_skipped_if_already_done():
    assert v2.plan_records([ev(1, 30)], {"pre": [1], "post": []}, NOW) == []

def test_post_fires_when_final_once():
    assert v2.plan_records([ev(1, -120, final=True, has_scores=True)], EMPTY, NOW) == [(1, "post")]

def test_post_skipped_if_recorded_or_not_final():
    assert v2.plan_records([ev(1, -120, final=True, has_scores=True)],
                           {"pre": [], "post": [1]}, NOW) == []
    assert v2.plan_records([ev(1, -120, final=False, has_scores=False)], EMPTY, NOW) == []

def test_md3_two_simultaneous_yield_two_pre_in_match_order():
    assert v2.plan_records([ev(8, 30), ev(7, 30)], EMPTY, NOW) == [(7, "pre"), (8, "pre")]
