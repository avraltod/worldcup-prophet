from tournament_2022 import GROUPS, BRACKET, RATINGS, TEAM_GROUP


def test_eight_groups_of_four_thirtytwo_teams():
    assert len(GROUPS) == 8
    assert all(len(ts) == 4 for ts in GROUPS.values())
    teams = [t for ts in GROUPS.values() for t in ts]
    assert len(teams) == 32 and len(set(teams)) == 32


def test_every_team_has_a_rating_and_a_group():
    teams = {t for ts in GROUPS.values() for t in ts}
    assert set(RATINGS) == teams
    assert set(TEAM_GROUP) == teams


def test_bracket_is_sixteen_and_references_are_valid():
    assert len(BRACKET) == 16
    assert len(BRACKET) & (len(BRACKET) - 1) == 0   # power of two
    for g, pos in BRACKET:
        assert g in GROUPS and pos in (1, 2)
    # all 8 groups appear, each with a 1 and a 2 slot
    for g in GROUPS:
        assert (g, 1) in BRACKET and (g, 2) in BRACKET
