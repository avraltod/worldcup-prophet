"""Pure ESPN lineup fetch + parse for the v2 recorder.
summary?event=<id> -> {"home": [starters], "away": [starters]} or None."""
import json
import urllib.request

SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary"


def parse_lineup(summary):
    """ESPN summary JSON -> {"home": [...], "away": [...]} or None if starters absent."""
    rosters = summary.get("rosters")
    if not rosters:
        return None
    out = {}
    for r in rosters:
        side = r.get("homeAway")
        if side not in ("home", "away"):
            continue
        starters = [p["athlete"]["displayName"]
                    for p in r.get("roster", [])
                    if p.get("starter") and p.get("athlete", {}).get("displayName")]
        if starters:
            out[side] = starters
    return out if out.get("home") and out.get("away") else None


def fetch_lineup(event_id, opener=urllib.request.urlopen):
    """Network: fetch + parse the lineup for an ESPN event id. opener is injectable."""
    with opener(f"{SUMMARY_URL}?event={event_id}", timeout=30) as resp:
        return parse_lineup(json.loads(resp.read().decode()))
