"""ESPN scoreboard fetch + group-fixture mapping for the live update pipeline.
Pure parsing/mapping functions (no side effects) + a thin urllib fetch.
Group stage only: maps ESPN events to GROUP_FIXTURES rows 4-75."""
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import GROUP_FIXTURES, canon

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


_FIX_ROW = {(_espn_name(h), _espn_name(a)): r for r, g, h, a in GROUP_FIXTURES}
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
        })
    return out


def map_to_fixture(home, away):
    """Return (matchno, fixture_home, fixture_away, reversed) or None.
    `reversed` is True when ESPN's home is the fixture's away team."""
    ch, ca = _espn_name(home), _espn_name(away)
    if (ch, ca) in _FIX_ROW:
        return (_FIX_ROW[(ch, ca)], *_FIX_NAMES[(ch, ca)], False)
    if (ca, ch) in _FIX_ROW:
        return (_FIX_ROW[(ca, ch)], *_FIX_NAMES[(ca, ch)], True)
    return None


def fetch_dates(dates, opener=urllib.request.urlopen):
    """Fetch + parse ESPN scoreboard for each YYYYMMDD string. opener is injectable."""
    rows = []
    for d in dates:
        with opener(f"{ESPN_URL}?dates={d}", timeout=30) as resp:
            rows += parse_scoreboard(json.loads(resp.read().decode()))
    return rows
