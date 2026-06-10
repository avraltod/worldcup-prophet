"""ESPN scoreboard fetch + group-fixture mapping for the live update pipeline.
Pure parsing/mapping functions (no side effects) + a thin urllib fetch.
Group stage only: maps ESPN events to official FIFA group-match numbers 1-72
(the keys condition.py / record_update.py / results_log['group'] use)."""
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import GROUP_FIXTURES, canon, ROW_MATCH

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

# ESPN displayName (lowercased) -> our GROUP_FIXTURES name, for names that differ.
# Extended/verified by Task 2 against the live 2026 schedule.
ESPN_ALIASES = {
    "usa": "United States",
    "korea republic": "South Korea",
    "ir iran": "Iran",
    "türkiye": "Turkey",
    "turkiye": "Turkey",
    "côte d'ivoire": "Ivory Coast",
    "cote d'ivoire": "Ivory Coast",
    "cabo verde": "Cape Verde",
    "dr congo": "Congo DR",
    "czech republic": "Czechia",
}


def _espn_name(name):
    """Normalize an ESPN display name to our fixture vocabulary, then canon()."""
    return canon(ESPN_ALIASES.get(name.strip().lower(), name))


# Map a canonical (home, away) name pair to its OFFICIAL FIFA match number (1-72),
# not the sheet row — results_log["group"] and condition.py are keyed by match number.
_FIX_MATCHNO = {(_espn_name(h), _espn_name(a)): ROW_MATCH[r] for r, g, h, a in GROUP_FIXTURES}
_FIX_NAMES = {(_espn_name(h), _espn_name(a)): (h, a) for r, g, h, a in GROUP_FIXTURES}


def _score(competitor):
    try:
        return int(competitor.get("score"))
    except (TypeError, ValueError):
        return None


def parse_scoreboard(payload):
    """ESPN scoreboard JSON -> list of {home, away, hg, ag, kickoff(UTC aware), final}."""
    out = []
    for ev in payload.get("events", []):
        comp = ev["competitions"][0]
        st = comp["status"]["type"]
        final = (st.get("state") == "post" and st.get("completed") is True
                 and st.get("detail") == "FT")
        sides = {c["homeAway"]: c for c in comp["competitors"]}
        if "home" not in sides or "away" not in sides:
            continue
        out.append({
            "home": sides["home"]["team"]["displayName"],
            "away": sides["away"]["team"]["displayName"],
            "hg": _score(sides["home"]),
            "ag": _score(sides["away"]),
            "kickoff": dt.datetime.fromisoformat(ev["date"].replace("Z", "+00:00")),
            "final": final,
            "event_id": ev.get("id"),
        })
    return out


def map_to_fixture(home, away):
    """Return (matchno, fixture_home, fixture_away, reversed) or None.
    `matchno` is the OFFICIAL FIFA match number (1-72). `reversed` is True when
    ESPN's home is the fixture's away team."""
    ch, ca = _espn_name(home), _espn_name(away)
    if (ch, ca) in _FIX_MATCHNO:
        return (_FIX_MATCHNO[(ch, ca)], *_FIX_NAMES[(ch, ca)], False)
    if (ca, ch) in _FIX_MATCHNO:
        return (_FIX_MATCHNO[(ca, ch)], *_FIX_NAMES[(ca, ch)], True)
    return None


def fetch_dates(dates, opener=urllib.request.urlopen):
    """Fetch + parse ESPN scoreboard for each YYYYMMDD string. opener is injectable."""
    rows = []
    for d in dates:
        with opener(f"{ESPN_URL}?dates={d}", timeout=30) as resp:
            rows += parse_scoreboard(json.loads(resp.read().decode()))
    return rows


def eligible_targets(parsed, results_log, now_utc, maturity_hours=3):
    """Decide what to publish. Returns (targets, holds, scored).
      targets: {"<matchno>": [hg, ag]} oriented to the fixture, for record_update.py
      scored:  [{"home","away","hg","ag"}] oriented to the fixture, for score_day.py
      holds:   list of human-readable reasons; NON-EMPTY means hold everything.
    Rules: ignore non-group pairings; skip already-recorded; silently exclude
    matches not yet matured (kickoff within maturity_hours of now); for matured
    group matches, HOLD on not-final / missing / out-of-bounds score."""
    done = set(results_log.get("group", {}))
    cutoff = now_utc - dt.timedelta(hours=maturity_hours)
    targets, scored, holds = {}, [], []
    for m in parsed:
        fx = map_to_fixture(m["home"], m["away"])
        if fx is None:
            continue                      # not a group fixture -> not our concern
        rownum, fh, fa, rev = fx
        key = str(rownum)
        if key in done:
            continue                      # idempotent: already recorded
        if m["kickoff"] > cutoff:
            continue                      # not matured yet -> exclude silently
        if not m["final"]:
            holds.append(f"match {rownum} ({fh} v {fa}) matured but not FT")
            continue
        if m["hg"] is None or m["ag"] is None:
            holds.append(f"match {rownum} ({fh} v {fa}) FT but missing score")
            continue
        if not (0 <= m["hg"] <= 19 and 0 <= m["ag"] <= 19):
            holds.append(f"match {rownum} score out of bounds: {m['hg']}-{m['ag']}")
            continue
        hg, ag = (m["ag"], m["hg"]) if rev else (m["hg"], m["ag"])
        targets[key] = [hg, ag]
        scored.append({"home": fh, "away": fa, "hg": hg, "ag": ag})
    if holds:
        return {}, holds, []
    return targets, holds, scored
