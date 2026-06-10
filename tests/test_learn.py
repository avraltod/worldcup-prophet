import pytest
from learn import lambda_expected

def test_equal_ratings_give_symmetric_lambdas():
    lh, la = lambda_expected(1800, 1800)
    assert abs(lh - la) < 1e-6
    assert 0.8 < lh < 2.0          # sane international goal rate

def test_stronger_team_has_higher_expected_goals():
    lh, la = lambda_expected(2000, 1700)
    assert lh > la

def test_weaker_home_has_lower_expected_goals():
    lh, la = lambda_expected(1600, 1900)
    assert lh < la

from learn import net_surprise, update_drift

def test_overperformance_is_positive_surprise():
    # generated 2.0 xG (expected 1.0), conceded 0.5 (expected 1.0)
    # (2-1) - (0.5-1) = 1 - (-0.5) = 1.5
    assert net_surprise(2.0, 1.0, 0.5, 1.0) == 1.5

def test_surprise_zero_when_as_expected():
    assert net_surprise(1.2, 1.2, 0.9, 0.9) == 0.0

def test_underperformance_is_negative_surprise():
    assert net_surprise(0.3, 1.0, 1.8, 1.0) == pytest.approx(-1.5)

def test_k_zero_means_only_decay():
    assert update_drift(40.0, 1.5, k=0.0, decay=0.95, bound=75.0) == 38.0  # 0.95*40

def test_step_is_decayed_drift_plus_k_times_surprise():
    # 0.95*10 + 60*0.5 = 9.5 + 30 = 39.5
    assert update_drift(10.0, 0.5, k=60.0, decay=0.95, bound=75.0) == 39.5

def test_step_clipped_to_bound_both_directions():
    assert update_drift(0.0, 5.0, k=60.0, decay=0.95, bound=75.0) == 75.0    # 300 -> 75
    assert update_drift(0.0, -5.0, k=60.0, decay=0.95, bound=75.0) == -75.0  # -300 -> -75

from learn import LearningTrack

def test_k_zero_track_never_moves():
    lt = LearningTrack({"A": 1800, "B": 1700}, k=0.0)
    lt.apply_match("A", "B", lam_obs_home=3.0, lam_obs_away=0.0)
    assert lt.rating("A") == 1800
    assert lt.rating("B") == 1700

def test_dominant_home_raises_home_lowers_away_symmetrically():
    lt = LearningTrack({"A": 1800, "B": 1800}, k=60.0, decay=0.95, bound=75.0)
    lt.apply_match("A", "B", lam_obs_home=3.0, lam_obs_away=0.2)  # A crushed it
    assert lt.rating("A") > 1800
    assert lt.rating("B") < 1800
    # equal start -> drifts are exact negatives (zero-sum)
    assert abs((lt.rating("A") - 1800) + (lt.rating("B") - 1800)) < 1e-9

def test_rating_is_baseline_plus_drift_and_unknown_team_is_baseline():
    lt = LearningTrack({"A": 1800, "B": 1800}, k=60.0)
    lt.apply_match("A", "B", lam_obs_home=2.5, lam_obs_away=0.5)
    assert lt.rating("A") == 1800 + lt.drift["A"]

def test_repeated_dominance_accumulates_but_bounded():
    lt = LearningTrack({"A": 1800, "B": 1800}, k=60.0, decay=0.95, bound=75.0)
    for _ in range(10):
        lt.apply_match("A", "B", lam_obs_home=3.0, lam_obs_away=0.0)
    # drift grows over repeats but the decay caps it below a runaway value
    assert lt.rating("A") - 1800 > 75            # accumulated beyond one game
    assert lt.rating("A") - 1800 < 75 / (1 - 0.95)  # but bounded by step/(1-decay)
