import pytest
from collect_match import build_performance_record

@pytest.mark.integration
def test_real_2022_match_produces_lambda_obs():
    # 633790 = Qatar vs Ecuador, 2022 WC opener (Ecuador won 2-0)
    rec = build_performance_record("633790", home="Qatar", away="Ecuador")
    assert rec["stats"]["home"]["team"] == "Qatar"
    assert "home" in rec["lambda_obs"] and "away" in rec["lambda_obs"]
    assert rec["lambda_obs"]["source"] == "proxy"     # no real-xG source wired
    # Ecuador (away) attacked more -> higher lambda than Qatar (had 0 shots)
    assert rec["lambda_obs"]["away"] > rec["lambda_obs"]["home"]
