"""Fetch the live prediction-market champion odds (Polymarket) and normalize to
our team names. Used by the recorder to log market-implied probabilities next to
the model's, so the two probability-revision trajectories can be compared."""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import canon

URL = "https://gamma-api.polymarket.com/events?slug=world-cup-winner"
DATA = Path(__file__).parent.parent / "data"
# our 48 teams (from the predictions), used to filter out placeholder markets
OUR_TEAMS = {p["home"] for p in json.loads((DATA / "group_predictions.json").read_text())} | \
            {p["away"] for p in json.loads((DATA / "group_predictions.json").read_text())}


def fetch_market_champion(timeout=20):
    """Return {team: de-vigged champion probability} for our 48 teams, or {} on failure."""
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "wc2026-tracker"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ev = json.loads(r.read())[0]
    except Exception as e:
        print(f"market fetch failed: {e}", file=sys.stderr)
        return {}
    raw = {}
    for m in ev.get("markets", []):
        name = m.get("groupItemTitle") or ""
        prices = m.get("outcomePrices")
        if isinstance(prices, str):
            try:
                prices = json.loads(prices)
            except Exception:
                continue
        if not prices:
            continue
        team = canon(name)
        if team in OUR_TEAMS:
            raw[team] = float(prices[0])
    s = sum(raw.values())
    if s <= 0:
        return {}
    return {t: round(p / s, 4) for t, p in raw.items()}   # de-vig


if __name__ == "__main__":
    mk = fetch_market_champion()
    print(f"market champion odds (de-vigged, {len(mk)} teams):")
    for t, p in sorted(mk.items(), key=lambda x: -x[1])[:12]:
        print(f"  {t:<16} {p*100:5.1f}%")
