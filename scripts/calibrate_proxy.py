"""One-time: fit proxy-xG coefficients (goals ~ a*SoT + b*other_shots) on the
2018 + 2022 World Cups, using only free data. Writes data/proxy_coef.json."""
import json
import subprocess
from pathlib import Path

import numpy as np
from collect_match import parse_statistics

SEASONS = ["world-cup-2018", "world-cup-2022"]
OUT = Path(__file__).parent.parent / "data" / "proxy_coef.json"


def _cli(*args):
    return json.loads(subprocess.run(
        ["sports-skills", "football", *args],
        capture_output=True, text=True, timeout=90).stdout)


def _matches(season):
    sched = _cli("get_season_schedule", f"--season_id={season}")
    return sched["data"]["schedules"]


def _goals(match):
    """(home_goals, away_goals) from a match's scores block.
    Verified shape (2022 WC): {'home': 0, 'away': 2} — plain integers."""
    sc = match.get("scores") or {}
    h, a = sc.get("home"), sc.get("away")
    if h is None or a is None:
        return None, None
    return int(h), int(a)


def collect_rows():
    """Return rows of (sot, other_shots, goals) — one per team per match."""
    rows = []
    for season in SEASONS:
        for m in _matches(season):
            if m.get("status") != "closed":
                continue
            hg, ag = _goals(m)
            if hg is None or ag is None:
                continue
            try:
                stats = parse_statistics(
                    _cli("get_event_statistics", f"--event_id={m['id']}"))
            except Exception:
                continue
            if "home" not in stats or "away" not in stats:
                continue
            rows.append((stats["home"]["sot"], stats["home"]["other_shots"], hg))
            rows.append((stats["away"]["sot"], stats["away"]["other_shots"], ag))
    return rows


def fit(rows):
    """Fit goals on [SoT, other_shots] by OLS, then clip coefficients to >= 0."""
    A = np.array([[r[0], r[1]] for r in rows], dtype=float)
    y = np.array([r[2] for r in rows], dtype=float)
    # closed-form OLS then clip to non-negative (simple, dependency-light)
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return {"sot": max(0.0, float(coef[0])), "other": max(0.0, float(coef[1]))}


if __name__ == "__main__":
    rows = collect_rows()
    coef = fit(rows)
    coef["n_team_matches"] = len(rows)
    OUT.write_text(json.dumps(coef, indent=2))
    print(f"fit on {len(rows)} team-matches -> {coef}")
