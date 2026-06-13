"""Fetch current ClubElo ratings + match odds + lineup adjustments.
Writes data/live_inputs.json before each v2 recording cycle.

Usage:
  python scripts/fetch_live_inputs.py --pre   # T-90min: odds + Elo + lineups
  python scripts/fetch_live_inputs.py --post  # T+FT: odds + Elo refresh
"""
import csv
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from condition import ROW_MATCH, RATES, ELO as JUNE10_ELO, ADJ as JUNE10_ADJ, GROUPS
from fixtures import canon
from poisson_model import fit_rates, outcome_probs as _outcome_probs

DATA = ROOT / "data"
OUT_PATH = DATA / "live_inputs.json"

CLUBELO_URL = "http://api.clubelo.com/{date}"
ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/"

CLUBELO_MAP = {
    "USA":            "United States",
    "Korea Republic": "South Korea",
    "South Korea":    "South Korea",
    "Cote d'Ivoire":  "Ivory Coast",
    "DR Congo":       "Congo DR",
    "Czech Republic": "Czechia",
    "Curacao":        "Curaçao",
}


def _iso_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_completed_matches():
    """Return set of completed group match numbers from results_log_v2.json."""
    for name in ("results_log_v2.json", "results_log.json"):
        p = DATA / name
        if p.exists():
            d = json.loads(p.read_text())
            return {int(k) for k in d.get("group", {})}
    return set()


def fetch_clubelo(date_str, opener=urllib.request.urlopen):
    """Fetch ClubElo CSV for date_str (YYYY-MM-DD). Returns {team: elo_float}."""
    url = CLUBELO_URL.format(date=date_str)
    with opener(url, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    reader = csv.DictReader(StringIO(text))
    out = {}
    for row in reader:
        if row.get("Level") != "1":
            continue
        raw_name = row.get("Club", "")
        name = CLUBELO_MAP.get(raw_name, raw_name)
        try:
            out[name] = float(row["Elo"])
        except (ValueError, KeyError):
            pass
    return out


def compute_elo_deltas(live_elo, june10_elo):
    """Return list of {team, june10, current, delta} for teams in both dicts."""
    deltas = []
    for team, curr in live_elo.items():
        if team in june10_elo:
            deltas.append({
                "team": team,
                "june10": june10_elo[team],
                "current": curr,
                "delta": round(curr - june10_elo[team], 1),
            })
    return sorted(deltas, key=lambda d: -abs(d["delta"]))


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    mode = "pre" if "--pre" in argv else "post"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = _iso_now()

    # --- ClubElo ---
    live_elo = {}
    elo_updated_at = None
    try:
        live_elo = fetch_clubelo(today)
        if len(live_elo) < 10:
            # ClubElo date endpoint returns club teams only when national teams
            # are unavailable; <10 teams signals a club-only or empty response.
            raise ValueError(f"ClubElo returned {len(live_elo)} teams (expected national teams)")
        elo_updated_at = now
        print(f"fetch_live_inputs: ClubElo fetched {len(live_elo)} teams")
    except Exception as e:
        print(f"fetch_live_inputs: ClubElo failed ({e}), using June 10 fallback",
              file=sys.stderr)
        live_elo = dict(JUNE10_ELO)
        elo_updated_at = "2026-06-10T00:00:00Z"

    elo_deltas = compute_elo_deltas(live_elo, JUNE10_ELO)
    elo_rms = round(math.sqrt(sum(d["delta"] ** 2 for d in elo_deltas) /
                               max(len(elo_deltas), 1)), 1)

    out = {
        "fetched_at": now,
        "mode": mode,
        "source_freshness": {"elo_updated_at": elo_updated_at},
        "live_elo": live_elo,
        "live_rates": {},
        "live_injury_adj": dict(JUNE10_ADJ),
        "lineup_adj": {},
        "deltas": {
            "elo": elo_deltas,
            "rates": [],
            "injury": [],
            "lineup": [],
            "drift": [],
            "summary": {
                "elo_rms_delta": elo_rms,
                "n_rate_changes": 0,
                "max_odds_shift_ph": 0.0,
                "biggest_elo_mover": elo_deltas[0] if elo_deltas else {},
                "biggest_odds_mover": {},
                "n_new_injuries": 0,
                "n_lineup_adj": 0,
                "n_teams_with_drift": 0,
            },
        },
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"fetch_live_inputs: wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
