"""CI-native box-score fetch: ESPN keyless summary endpoint -> shot stats for a
completed match, cached to data/match_stats/ so editions are reproducible
offline. Hold-on-doubt: any missing/ambiguous field returns None rather than a
guess. (collect_match.fetch_match_stats needs the local sports-skills CLI and
is the manual fallback only.)"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_results as fr

ROOT = Path(__file__).resolve().parent.parent
STATS_DIR = ROOT / "data" / "match_stats"
SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={}"

_SOT_KEYS = ("shotsOnTarget", "shotsOnGoal")
_TOTAL_KEYS = ("totalShots", "shots")
_POSS_KEYS = ("possessionPct",)


def _fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _num(s):
    if s is None:
        return None
    try:
        return float(str(s).rstrip("%"))
    except ValueError:
        return None


def _first(stats_by_name, keys):
    for k in keys:
        v = _num(stats_by_name.get(k))
        if v is not None:
            return v
    return None


def parse_summary(payload):
    """ESPN summary JSON -> {'home': {team, sot, other_shots, total_shots,
    possession}, 'away': {...}} or None on any doubt."""
    try:
        comps = payload["header"]["competitions"][0]["competitors"]
        side_by_id = {c["team"]["id"]: c["homeAway"] for c in comps}
        teams = payload["boxscore"]["teams"]
    except (KeyError, IndexError, TypeError):
        return None
    out = {}
    for t in teams:
        side = side_by_id.get(t.get("team", {}).get("id"))
        if side not in ("home", "away"):
            return None
        by_name = {s.get("name"): s.get("displayValue")
                   for s in t.get("statistics", [])}
        sot = _first(by_name, _SOT_KEYS)
        total = _first(by_name, _TOTAL_KEYS)
        if sot is None or total is None or total < sot:
            return None
        # ESPN's totalShots includes blocked shots (match 1: total 16 = 4 SoT
        # + 5 blockedShots + 7 off target), so total - sot equals the
        # off_target + blocked definition proxy_coef.json was calibrated on.
        out[side] = {"team": t["team"].get("displayName", ""),
                     "sot": sot, "other_shots": max(0.0, total - sot),
                     "total_shots": total,
                     "possession": _first(by_name, _POSS_KEYS)}
    return out if set(out) == {"home", "away"} else None


def find_event_id(match, kickoff_iso):
    """Scoreboard lookup on the kickoff date (UTC, +/- 1 day) -> event id."""
    day = datetime.fromisoformat(kickoff_iso.replace("Z", "+00:00"))
    for d in (day, day - timedelta(days=1), day + timedelta(days=1)):
        try:
            payload = _fetch_json(fr.ESPN_URL + "?dates=" + d.strftime("%Y%m%d"))
        except Exception:
            continue
        for e in fr.parse_scoreboard(payload):
            hit = fr.map_to_fixture(e["home"], e["away"])
            if hit and hit[0] == match and e.get("event_id"):
                return e["event_id"]
    return None


def get_stats(match, kickoff_iso):
    """Cache-first stats for one finished match. Returns the parsed stats dict
    or None (caller queues and retries next run)."""
    cache = STATS_DIR / f"M{match:03d}.json"
    if cache.exists():
        return json.loads(cache.read_text())["stats"]
    event_id = find_event_id(match, kickoff_iso)
    if event_id is None:
        return None
    try:
        parsed = parse_summary(_fetch_json(SUMMARY_URL.format(event_id)))
    except Exception:
        return None
    if parsed is None:
        return None
    STATS_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(
        {"match": match, "event_id": event_id, "stats": parsed},
        ensure_ascii=False, indent=1))
    return parsed
