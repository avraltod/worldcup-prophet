"""Convert a match's shot stats into lambda_obs (expected-goals signal)."""
import json
from pathlib import Path

_COEF_PATH = Path(__file__).parent.parent / "data" / "proxy_coef.json"


def load_coef():
    """Calibrated proxy coefficients (written by calibrate_proxy.py)."""
    return json.loads(_COEF_PATH.read_text())


def proxy_xg(sot, other_shots, coef=None):
    """Poor-man's xG: c_sot * SoT + c_other * other_shots, floored at 0."""
    c = coef if coef is not None else load_coef()
    return max(0.0, c["sot"] * sot + c["other"] * other_shots)


def compute_lambda_obs(stats, real_xg=None, coef=None):
    """stats = parse_statistics output. real_xg = {'home','away'} or None.
    Returns {'home': λ, 'away': λ, 'source': 'real'|'proxy'}."""
    if real_xg is not None:
        return {"home": real_xg["home"], "away": real_xg["away"], "source": "real"}
    c = coef if coef is not None else load_coef()
    return {
        "home": proxy_xg(stats["home"]["sot"], stats["home"]["other_shots"], c),
        "away": proxy_xg(stats["away"]["sot"], stats["away"]["other_shots"], c),
        "source": "proxy",
    }
