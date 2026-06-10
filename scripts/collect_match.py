"""Pull a finished match box-score from the free football data tool and
normalize it into clean numeric home/away stats."""
import json
import subprocess

# raw stat key -> clean name (only the fields we use downstream)
_KEEP = {
    "ball_possession": "possession",
    "shots_total": "shots",
    "shots_on_target": "sot",
    "shots_off_target": "off_target",
    "shots_blocked": "blocked",
    "corner_kicks": "corners",
    "fouls": "fouls",
    "offsides": "offsides",
    "yellow_cards": "yellow",
    "red_cards": "red",
    "passes_total": "passes",
}


def _num(s):
    """'47.1' -> 47.1, '5' -> 5 (int), '' / None / non-numeric -> 0."""
    if s in (None, ""):
        return 0
    try:
        f = float(s)
    except (TypeError, ValueError):
        return 0
    return int(f) if f.is_integer() else f


def parse_statistics(raw):
    """raw = JSON dict from get_event_statistics.
    Returns {'home': {clean stats}, 'away': {...}}; adds derived 'other_shots'."""
    out = {}
    for team in raw["data"]["teams"]:
        side = team["qualifier"]                 # 'home' | 'away'
        st = team.get("statistics", {})
        clean = {name: _num(st.get(key)) for key, name in _KEEP.items()}
        clean["team"] = team["team"]["name"]
        clean["other_shots"] = clean["off_target"] + clean["blocked"]
        out[side] = clean
    return out


def fetch_match_stats(match_id):
    """Network: call the data tool and return parse_statistics(raw)."""
    raw = subprocess.run(
        ["sports-skills", "football", "get_event_statistics",
         f"--event_id={match_id}"],
        capture_output=True, text=True, timeout=60).stdout
    return parse_statistics(json.loads(raw))


def build_performance_record(match_id, home=None, away=None):
    """Full record for one finished match: stats + lambda_obs (real-xG or proxy)."""
    from performance import compute_lambda_obs   # local import avoids cycle
    from fetch_xg import fetch_real_xg
    stats = fetch_match_stats(match_id)
    real = fetch_real_xg(match_id, home, away)
    lam = compute_lambda_obs(stats, real_xg=real)
    return {"match_id": str(match_id), "stats": stats, "lambda_obs": lam}
