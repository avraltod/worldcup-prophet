"""Best-effort FREE real-xG fetch (FotMob / FBref). Contract: returns
{'home': float, 'away': float} when available, else None. NEVER raises —
callers fall back to the shots-based proxy. Free sources only."""


def fetch_real_xg(match_id, home=None, away=None):
    """Try free sources for real xG; return dict or None on any failure."""
    try:
        return _fetch_fotmob(match_id, home, away)
    except Exception:
        return None


def _fetch_fotmob(match_id, home, away):
    # Live free scrape is wired in a later plan (fragile; needs live iteration).
    # Until then, signal "not available" so the proxy is used.
    raise NotImplementedError("real-xG source not wired yet; using proxy")
