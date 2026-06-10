from replay import run_replay, champion_dist

# synthetic 2 groups of 4 -> top 2 -> 4-team knockout (same shape as the sim tests)
def _structure():
    rr = lambda ts: [(ts[i], ts[j]) for i in range(4) for j in range(i + 1, 4)]
    A = ["A1", "A2", "A3", "A4"]
    B = ["B1", "B2", "B3", "B4"]
    return {"groups": {"A": A, "B": B}, "fixtures": {"A": rr(A), "B": rr(B)},
            "bracket": [("A", 1), ("B", 2), ("B", 1), ("A", 2)]}

def _ratings():
    return {"A1": 2200, "A2": 1750, "A3": 1700, "A4": 1650,
            "B1": 1900, "B2": 1750, "B3": 1700, "B4": 1650}

def test_champion_dist_extracts_probs():
    out = {"X": {"champion": 0.6, "reached": {1: 0.9}},
           "Y": {"champion": 0.4, "reached": {1: 0.8}}}
    assert champion_dist(out) == {"X": 0.6, "Y": 0.4}

def test_replay_has_both_tracks_with_baseline_plus_one_per_game():
    games = [{"home": "A1", "away": "A2", "kind": "group", "result": (1, 0),
              "lam_obs": {"home": 1.5, "away": 0.5}}]
    traj = run_replay(_structure(), _ratings(), games, N=1500, seed=7)
    assert set(traj) == {"frozen", "learning"}
    # one t=0 baseline snapshot + one per game
    assert len(traj["frozen"]) == 2 and len(traj["learning"]) == 2
    for snaps in traj.values():
        for s in snaps:
            assert abs(sum(s["champion"].values()) - 1.0) < 1e-9
            assert "kl_from_prev" in s

def test_big_result_carries_more_information_than_a_calm_one():
    # game 1: bottom seeds draw (little news). game 2: top seed A1 loses (big news)
    games = [
        {"home": "A3", "away": "A4", "kind": "group", "result": (1, 1),
         "lam_obs": {"home": 1.0, "away": 1.0}},
        {"home": "A1", "away": "A2", "kind": "group", "result": (0, 3),
         "lam_obs": {"home": 0.3, "away": 2.5}},
    ]
    traj = run_replay(_structure(), _ratings(), games, N=3000, seed=7)
    kl_calm = traj["frozen"][1]["kl_from_prev"]   # after the A3-A4 draw
    kl_upset = traj["frozen"][2]["kl_from_prev"]  # after A1 loses
    assert kl_upset > kl_calm

def test_learning_diverges_from_frozen_on_a_dominated_winner():
    # A1 wins all three group games 1-0 but is OUT-xG'd every time (lucky wins).
    # Frozen keeps A1 strong (it qualified); learning weakens A1 (poor xG) ->
    # A1's champion prob is lower on the learning track.
    g = lambda opp: {"home": "A1", "away": opp, "kind": "group", "result": (1, 0),
                     "lam_obs": {"home": 0.3, "away": 1.8}}
    games = [g("A2"), g("A3"), g("A4")]
    traj = run_replay(_structure(), _ratings(), games, N=4000, seed=7)
    fz = traj["frozen"][-1]["champion"]["A1"]
    ln = traj["learning"][-1]["champion"]["A1"]
    assert ln < fz
