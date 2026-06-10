from performance import proxy_xg

COEF = {"sot": 0.30, "other": 0.03}   # explicit coef so the test is deterministic

def test_proxy_is_linear_in_shots():
    # 3 on target, 4 other -> 0.9 + 0.12 = 1.02
    assert round(proxy_xg(3, 4, COEF), 4) == 1.02

def test_proxy_zero_when_no_shots():
    assert proxy_xg(0, 0, COEF) == 0.0

def test_proxy_never_negative():
    assert proxy_xg(0, 0, {"sot": -1, "other": -1}) == 0.0

from performance import compute_lambda_obs

STATS = {
    "home": {"sot": 3, "other_shots": 4},
    "away": {"sot": 1, "other_shots": 2},
}

def test_uses_proxy_when_real_xg_is_none():
    out = compute_lambda_obs(STATS, real_xg=None, coef=COEF)
    assert out["source"] == "proxy"
    assert round(out["home"], 4) == 1.02        # 0.30*3 + 0.03*4
    assert round(out["away"], 4) == 0.36        # 0.30*1 + 0.03*2

def test_prefers_real_xg_when_present():
    out = compute_lambda_obs(STATS, real_xg={"home": 2.1, "away": 0.4}, coef=COEF)
    assert out["source"] == "real"
    assert out["home"] == 2.1 and out["away"] == 0.4
