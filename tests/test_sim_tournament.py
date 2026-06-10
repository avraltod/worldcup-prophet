import random
from sim_tournament import win_prob, simulate_knockout, group_standings

def test_win_prob_is_half_at_equal_ratings():
    assert win_prob(1800, 1800) == 0.5

def test_win_prob_favors_stronger():
    assert win_prob(2000, 1700) > 0.7
    assert win_prob(1700, 2000) < 0.3

def test_knockout_strongest_seed_wins_most():
    ratings = {"S": 2300, "w1": 1600, "w2": 1600, "w3": 1600}
    seeds = ["S", "w1", "w2", "w3"]            # 4-team bracket
    rng = random.Random(1)
    champs = {}
    for _ in range(3000):
        depth = simulate_knockout(seeds, ratings, {}, rng)
        champ = max(depth, key=depth.get)
        champs[champ] = champs.get(champ, 0) + 1
    assert champs["S"] / 3000 > 0.7           # dominant team wins most

def test_knockout_depth_entrant_is_one_champion_is_rounds_plus_one():
    ratings = {"S": 3000, "w1": 1000, "w2": 1000, "w3": 1000}  # S always wins
    depth = simulate_knockout(["S", "w1", "w2", "w3"], ratings, {}, random.Random(0))
    assert depth["S"] == 3                     # 2 rounds won + 1 = champion depth
    assert depth["w1"] == 1                    # entrant, lost first round

def test_knockout_respects_played_result():
    ratings = {"S": 3000, "x": 1000, "a": 1500, "b": 1500}
    # S would dominate, but we record that x beat S in round 1
    depth = simulate_knockout(["S", "x", "a", "b"], ratings,
                              {("S", "x"): "x"}, random.Random(0))
    assert depth["x"] >= 2                     # x advanced past S
    assert depth["S"] == 1                     # S out in round 1

from sim_tournament import group_standings

def test_standings_deterministic_when_all_results_given():
    teams = ["A", "B", "C", "D"]
    fixtures = [("A", "B"), ("A", "C"), ("A", "D"),
                ("B", "C"), ("B", "D"), ("C", "D")]
    # A wins all, B second, C third, D loses all
    results = {("A", "B"): (2, 0), ("A", "C"): (2, 0), ("A", "D"): (3, 0),
               ("B", "C"): (1, 0), ("B", "D"): (2, 0), ("C", "D"): (1, 0)}
    order = group_standings(teams, fixtures, {}, results, random.Random(0))
    assert order == ["A", "B", "C", "D"]

def test_standings_breaks_ties_on_goal_difference():
    teams = ["A", "B", "C", "D"]
    fixtures = [("A", "B"), ("C", "D"), ("A", "C"), ("B", "D"),
                ("A", "D"), ("B", "C")]
    # A and B both beat C and D and draw each other; A has bigger GD
    results = {("A", "B"): (1, 1), ("C", "D"): (0, 0),
               ("A", "C"): (5, 0), ("B", "D"): (1, 0),
               ("A", "D"): (5, 0), ("B", "C"): (1, 0)}
    order = group_standings(teams, fixtures, {}, results, random.Random(0))
    assert order[0] == "A" and order[1] == "B"   # A ahead of B on GD

from sim_tournament import simulate

# synthetic: 2 groups of 4 -> top 2 each -> 4-team knockout
def _structure():
    rr = lambda ts: [(ts[i], ts[j]) for i in range(4) for j in range(i + 1, 4)]
    A = ["A1", "A2", "A3", "A4"]
    B = ["B1", "B2", "B3", "B4"]
    return {
        "groups": {"A": A, "B": B},
        "fixtures": {"A": rr(A), "B": rr(B)},
        # R-of-4 seeding order: (A1 v B2), (B1 v A2) -> winners meet in final
        "bracket": [("A", 1), ("B", 2), ("B", 1), ("A", 2)],
    }

def _ratings():
    return {"A1": 2200, "A2": 1750, "A3": 1700, "A4": 1650,
            "B1": 1900, "B2": 1750, "B3": 1700, "B4": 1650}

def test_simulate_returns_probabilities_for_every_team():
    out = simulate(_structure(), _ratings(), N=2000, seed=7)
    assert set(out) == set(_ratings())
    total_champ = sum(o["champion"] for o in out.values())
    assert abs(total_champ - 1.0) < 1e-9        # champion prob sums to 1
    for o in out.values():
        assert 0.0 <= o["champion"] <= 1.0

def test_strongest_team_is_most_likely_champion():
    out = simulate(_structure(), _ratings(), N=4000, seed=7)
    best = max(out, key=lambda t: out[t]["champion"])
    assert best == "A1"
    assert out["A1"]["champion"] > out["B1"]["champion"]

def test_reached_is_monotone_decreasing_by_round():
    out = simulate(_structure(), _ratings(), N=2000, seed=7)
    r = out["A1"]["reached"]                     # {1: reach semifinal, 2: reach final}
    assert r[1] >= r[2] >= out["A1"]["champion"]

def test_conditioning_on_results_shifts_the_forecast():
    # force A1 to lose all three group games -> it should almost never be champion
    losses = {("A1", "A2"): (0, 3), ("A1", "A3"): (0, 3), ("A1", "A4"): (0, 3)}
    base = simulate(_structure(), _ratings(), N=3000, seed=7)
    cond = simulate(_structure(), _ratings(), group_results=losses, N=3000, seed=7)
    assert cond["A1"]["champion"] < base["A1"]["champion"]
    assert cond["A1"]["champion"] < 0.10
