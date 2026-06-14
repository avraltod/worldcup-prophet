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


def fetch_odds(api_key, unplayed_rows, opener=urllib.request.urlopen):
    """Fetch H2H odds for WC 2026. Returns ({row: [lh, la]}, [detail_dicts]).

    unplayed_rows: set of row ints (from condition.ROW_MATCH) to fetch for.
    Returns ({}, []) if api_key is falsy (graceful degradation).
    """
    if not api_key:
        return {}, []

    row_lookup = {}
    for row in unplayed_rows:
        lh, la, home, away = RATES[row]
        row_lookup[(canon(home), canon(away))] = (row, home, away, False)
        row_lookup[(canon(away), canon(home))] = (row, home, away, True)   # reversed

    params = (f"?apiKey={api_key}&regions=us&markets=h2h"
              f"&oddsFormat=decimal&sportKey=soccer_fifa_world_cup")
    url = ODDS_URL + params
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "wc2026-tracker"})
        with opener(req, timeout=30) as resp:
            events = json.loads(resp.read())
    except Exception as e:
        print(f"fetch_live_inputs: odds API failed ({e})", file=sys.stderr)
        return {}, []

    live_rates, details = {}, []
    for ev in events:
        h = canon(ev.get("home_team", ""))
        a = canon(ev.get("away_team", ""))
        entry = row_lookup.get((h, a))
        if entry is None:
            continue
        row, home, away, reversed_fixture = entry

        # Take first available H2H market from any bookmaker
        prices = None
        for bk in ev.get("bookmakers", []):
            for mkt in bk.get("markets", []):
                if mkt.get("key") != "h2h":
                    continue
                oc = {o["name"]: float(o["price"]) for o in mkt.get("outcomes", [])}
                if "Draw" in oc and len(oc) == 3:
                    prices = oc
                    break
            if prices:
                break
        if not prices:
            continue

        home_price = prices.get(ev["home_team"])
        away_price = next((v for k, v in prices.items()
                           if k not in ("Draw", ev["home_team"])), None)
        if not home_price or not away_price:
            continue

        inv = [1 / home_price, 1 / prices["Draw"], 1 / away_price]
        s = sum(inv)
        ph, pd, pa = inv[0] / s, inv[1] / s, inv[2] / s
        lh_fit, la_fit = fit_rates(ph, pd, pa)

        june10_ph = round(_outcome_probs(RATES[row][0], RATES[row][1])[0], 3)
        if reversed_fixture:
            live_rates[row] = [la_fit, lh_fit]
        else:
            live_rates[row] = [lh_fit, la_fit]

        details.append({
            "row": row, "fixture": f"{home} v {away}",
            "june10_ph": june10_ph, "live_ph": round(ph, 3),
            "delta_ph": round(ph - june10_ph, 3),
            "june10_lh": RATES[row][0], "live_lh": live_rates[row][0],
        })

    return live_rates, details


def compute_lineup_adj(team, side, lineup, key_players):
    """Compute Elo deduction for team based on absent key players.

    side: "home" or "away" — which side of the lineup dict to check.
    key_players: {team: {player_name: positive_magnitude}} from key_player_elo_adj.json.
    Returns negative int (deduction) or 0.
    """
    if team not in key_players:
        return 0
    if side not in lineup:
        return 0
    starters = set(lineup.get(side, []))
    total_deduction = 0
    for player, magnitude in key_players[team].items():
        if player not in starters:
            total_deduction -= magnitude
    return total_deduction


def compute_injury_deltas(live_inj, june10_adj):
    """Return list of {team, june10, current, delta} where current != june10."""
    deltas = []
    all_teams = set(live_inj) | set(june10_adj)
    for team in all_teams:
        curr = live_inj.get(team, 0)
        base = june10_adj.get(team, 0)
        if curr != base:
            deltas.append({"team": team, "june10": base, "current": curr,
                           "delta": curr - base})
    return deltas


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

    # --- Odds API ---
    api_key = os.environ.get("ODDS_API_KEY", "")
    completed = _load_completed_matches()
    unplayed_rows = {r for r, m in ROW_MATCH.items() if m not in completed and m <= 72}
    odds_fetched_at = None
    live_rates_dict, rate_details = {}, []
    if api_key:
        try:
            live_rates_dict, rate_details = fetch_odds(api_key, unplayed_rows)
            odds_fetched_at = now
            print(f"fetch_live_inputs: odds fetched {len(live_rates_dict)} fixtures")
        except Exception as e:
            print(f"fetch_live_inputs: odds failed ({e})", file=sys.stderr)
    else:
        print("fetch_live_inputs: ODDS_API_KEY not set, skipping odds fetch")

    # --- Drift summary from learning_state_2026.json ---
    drift_details = []
    n_drift = 0
    state_path = DATA / "learning_state_2026.json"
    if state_path.exists():
        st = json.loads(state_path.read_text())
        drift = st.get("drift", {})
        drift_details = [{"team": t, "drift": round(d, 2)}
                         for t, d in sorted(drift.items(), key=lambda kv: -abs(kv[1]))]
        n_drift = len(drift_details)

    # --- Injury deltas ---
    out_injury_adj = dict(JUNE10_ADJ)
    inj_deltas = compute_injury_deltas(out_injury_adj, JUNE10_ADJ)
    n_new_inj = len(inj_deltas)

    out = {
        "fetched_at": now,
        "mode": mode,
        "source_freshness": {
            "elo_updated_at": elo_updated_at,
            "odds_fetched_at": odds_fetched_at,
        },
        "live_elo": live_elo,
        "live_rates": {str(r): v for r, v in live_rates_dict.items()},
        "live_injury_adj": out_injury_adj,
        "lineup_adj": {},
        "deltas": {
            "elo": elo_deltas,
            "rates": rate_details,
            "injury": inj_deltas,
            "lineup": [],
            "drift": drift_details,
            "summary": {
                "elo_rms_delta": elo_rms,
                "n_rate_changes": len(rate_details),
                "max_odds_shift_ph": round(max((abs(d["delta_ph"]) for d in rate_details), default=0.0), 3),
                "biggest_elo_mover": elo_deltas[0] if elo_deltas else {},
                "biggest_odds_mover": max(rate_details, key=lambda d: abs(d["delta_ph"]), default={}),
                "n_new_injuries": n_new_inj,
                "n_lineup_adj": 0,
                "n_teams_with_drift": n_drift,
            },
        },
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"fetch_live_inputs: wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
