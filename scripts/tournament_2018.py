"""2018 World Cup (Russia) structure + approximate pre-tournament (June 2018)
Elo ratings, for the Prophet replay — a second tuning/validation point alongside
2022. Groups and bracket are historical fact; names match the free feed; ratings
are approximate eloratings.net-style June-2018 values (the frozen baseline is a
fixed reference, so approximations are fine).
"""

GROUPS = {
    "A": ["Russia", "Saudi Arabia", "Egypt", "Uruguay"],
    "B": ["Portugal", "Spain", "Morocco", "Iran"],
    "C": ["France", "Australia", "Peru", "Denmark"],
    "D": ["Argentina", "Iceland", "Croatia", "Nigeria"],
    "E": ["Brazil", "Switzerland", "Costa Rica", "Serbia"],
    "F": ["Germany", "Mexico", "Sweden", "South Korea"],
    "G": ["Belgium", "Panama", "Tunisia", "England"],
    "H": ["Poland", "Senegal", "Colombia", "Japan"],
}

# same single-elim seeding order as 2022 (1A-2B, 1C-2D, ... folded into the bracket)
BRACKET = [
    ("A", 1), ("B", 2), ("C", 1), ("D", 2),
    ("E", 1), ("F", 2), ("G", 1), ("H", 2),
    ("B", 1), ("A", 2), ("D", 1), ("C", 2),
    ("F", 1), ("E", 2), ("H", 1), ("G", 2),
]

# approximate pre-tournament Elo (June 2018)
RATINGS = {
    "Russia": 1685, "Saudi Arabia": 1591, "Egypt": 1665, "Uruguay": 1894,
    "Portugal": 1968, "Spain": 2042, "Morocco": 1719, "Iran": 1779,
    "France": 1998, "Australia": 1709, "Peru": 1906, "Denmark": 1845,
    "Argentina": 1986, "Iceland": 1741, "Croatia": 1855, "Nigeria": 1683,
    "Brazil": 2131, "Switzerland": 1887, "Costa Rica": 1751, "Serbia": 1763,
    "Germany": 2076, "Mexico": 1858, "Sweden": 1799, "South Korea": 1744,
    "Belgium": 1933, "Panama": 1685, "Tunisia": 1652, "England": 1945,
    "Poland": 1814, "Senegal": 1751, "Colombia": 1928, "Japan": 1696,
}

TEAM_GROUP = {t: g for g, ts in GROUPS.items() for t in ts}
