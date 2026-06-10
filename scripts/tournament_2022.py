"""2022 World Cup structure + approximate pre-tournament (Nov 2022) Elo ratings,
for the Prophet replay (Plan 5). Groups and the knockout bracket are historical
fact; team names match the free data feed exactly. Ratings are approximate
eloratings.net-style values as of the tournament start — the frozen baseline is a
fixed reference, so approximate values are fine for the learning-vs-frozen study.

Group fixtures are NOT hardcoded here: the replay runner builds them (and the
results) from the actual schedule so home/away orientation matches the feed.
"""

# group -> the four teams (exact feed names)
GROUPS = {
    "A": ["Qatar", "Ecuador", "Senegal", "Netherlands"],
    "B": ["England", "Iran", "United States", "Wales"],
    "C": ["Argentina", "Saudi Arabia", "Mexico", "Poland"],
    "D": ["France", "Australia", "Denmark", "Tunisia"],
    "E": ["Spain", "Costa Rica", "Germany", "Japan"],
    "F": ["Belgium", "Canada", "Morocco", "Croatia"],
    "G": ["Brazil", "Serbia", "Switzerland", "Cameroon"],
    "H": ["Portugal", "Ghana", "Uruguay", "South Korea"],
}

# Round-of-16 seeding order, flat (group, finishing-position). Folding adjacent
# pairs reproduces the actual 2022 bracket:
#   R16: 1A-2B, 1C-2D, 1E-2F, 1G-2H, 1B-2A, 1D-2C, 1F-2E, 1H-2G
#   -> QF: (1A/2B v 1C/2D), (1E/2F v 1G/2H), (1B/2A v 1D/2C), (1F/2E v 1H/2G)
BRACKET = [
    ("A", 1), ("B", 2), ("C", 1), ("D", 2),
    ("E", 1), ("F", 2), ("G", 1), ("H", 2),
    ("B", 1), ("A", 2), ("D", 1), ("C", 2),
    ("F", 1), ("E", 2), ("H", 1), ("G", 2),
]

# approximate pre-tournament Elo (Nov 2022)
RATINGS = {
    "Qatar": 1680, "Ecuador": 1789, "Senegal": 1815, "Netherlands": 2040,
    "England": 1998, "Iran": 1817, "United States": 1837, "Wales": 1790,
    "Argentina": 2073, "Saudi Arabia": 1638, "Mexico": 1814, "Poland": 1814,
    "France": 2074, "Australia": 1714, "Denmark": 1979, "Tunisia": 1687,
    "Spain": 2048, "Costa Rica": 1601, "Germany": 1962, "Japan": 1690,
    "Belgium": 2025, "Canada": 1709, "Morocco": 1737, "Croatia": 1957,
    "Brazil": 2169, "Serbia": 1801, "Switzerland": 1899, "Cameroon": 1610,
    "Portugal": 2004, "Ghana": 1567, "Uruguay": 1936, "South Korea": 1729,
}

# reverse map: team -> its group letter
TEAM_GROUP = {t: g for g, ts in GROUPS.items() for t in ts}
