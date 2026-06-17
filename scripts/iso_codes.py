"""Team-name -> (ISO 3166-1 alpha-2 for worldflags, 3-letter text code) map for
the 2026 finalists, plus LaTeX helpers to shorten the country columns. Text uses
ISO 3166-1 alpha-3 where it exists; England/Scotland (no ISO3) use the customary
football codes and carry no worldflags subdivision flag. The flag is emitted via
\\teamflag{ISO2}, a macro defined in the paper preamble that degrades to nothing
when worldflags is unavailable, so these tags never break a build."""

# team -> (iso2_for_flag, code3_for_text); iso2 "" means "no flag"
TEAM_ISO = {
    "Mexico": ("MX", "MEX"), "South Africa": ("ZA", "ZAF"),
    "South Korea": ("KR", "KOR"), "Czechia": ("CZ", "CZE"),
    "Canada": ("CA", "CAN"), "Bosnia and Herzegovina": ("BA", "BIH"),
    "United States": ("US", "USA"), "Paraguay": ("PY", "PRY"),
    "Haiti": ("HT", "HTI"), "Scotland": ("", "SCO"),
    "Australia": ("AU", "AUS"), "Turkey": ("TR", "TUR"),
    "Brazil": ("BR", "BRA"), "Morocco": ("MA", "MAR"),
    "Qatar": ("QA", "QAT"), "Switzerland": ("CH", "CHE"),
    "Ivory Coast": ("CI", "CIV"), "Ecuador": ("EC", "ECU"),
    "Germany": ("DE", "DEU"), "Curaçao": ("CW", "CUW"), "Curacao": ("CW", "CUW"),
    "Netherlands": ("NL", "NLD"), "Japan": ("JP", "JPN"),
    "Sweden": ("SE", "SWE"), "Tunisia": ("TN", "TUN"),
    "Saudi Arabia": ("SA", "SAU"), "Uruguay": ("UY", "URY"),
    "Spain": ("ES", "ESP"), "Cape Verde": ("CV", "CPV"),
    "Iran": ("IR", "IRN"), "New Zealand": ("NZ", "NZL"),
    "Belgium": ("BE", "BEL"), "Egypt": ("EG", "EGY"),
    "France": ("FR", "FRA"), "Senegal": ("SN", "SEN"),
    "Iraq": ("IQ", "IRQ"), "Norway": ("NO", "NOR"),
    "Argentina": ("AR", "ARG"), "Algeria": ("DZ", "DZA"),
    "Austria": ("AT", "AUT"), "Jordan": ("JO", "JOR"),
    "Portugal": ("PT", "PRT"), "Congo DR": ("CD", "COD"),
    "England": ("", "ENG"), "Croatia": ("HR", "HRV"),
    "Panama": ("PA", "PAN"), "Ghana": ("GH", "GHA"),
    "Colombia": ("CO", "COL"), "Uzbekistan": ("UZ", "UZB"),
}


def code3(team):
    """3-letter text code (ISO3 where it exists), or the name if unknown."""
    return TEAM_ISO.get(team, ("", team))[1]


def team_tag(team):
    """3-letter ISO3-style code (e.g. Bosnia and Herzegovina -> BIH), shortening
    the country columns. Flags are intentionally omitted: rendering ~150
    worldflags flags across these tables exceeds TeX's main memory and breaks
    the build (and CI), so codes alone carry the width saving safely."""
    return TEAM_ISO.get(team, ("", team))[1]


def fixture_tag(fixture):
    """'Home v Away' -> 'flag CODE v flag CODE'; passthrough if unsplittable.
    A trailing ', ...' suffix (e.g. ', MD1') is preserved verbatim."""
    core, suffix = (fixture or ""), ""
    if "," in core:
        core, rest = core.split(",", 1)
        suffix = "," + rest
    if " v " in core:
        home, away = core.split(" v ", 1)
        return f"{team_tag(home.strip())} v {team_tag(away.strip())}{suffix}"
    return fixture
