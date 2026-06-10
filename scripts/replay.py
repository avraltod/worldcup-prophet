"""Two-track replay orchestrator. Steps an ordered game list, conditioning the
simulation on each result, and emits a champion-distribution trajectory for the
frozen track (baseline ratings) and the learning track (LearningTrack ratings).
Each snapshot carries the KL information content vs the previous snapshot."""
from sim_tournament import simulate
from learn import LearningTrack
from snapshot import kl_divergence


def champion_dist(sim_out):
    """Extract {team: champion_prob} from a sim_tournament.simulate result."""
    return {t: sim_out[t]["champion"] for t in sim_out}


def _snapshot(traj, prev, name, index, home, away, dist):
    kl = kl_divergence(dist, prev[name]) if prev[name] is not None else 0.0
    traj[name].append({"game_index": index, "home": home, "away": away,
                       "champion": dist, "kl_from_prev": kl})
    prev[name] = dist


def run_replay(structure, baseline, games, N=4000, seed=2026, k=50.0):
    """games: ordered list of {home, away, kind, result, lam_obs}. Returns
    {"frozen": [snap...], "learning": [snap...]} with a t=0 baseline snapshot
    (game_index -1) plus one snapshot per game on each track. k is the learning
    rate of the learning track (k=0 reproduces the frozen track)."""
    groups, ko = {}, {}
    learn = LearningTrack(baseline, k=k)
    traj = {"frozen": [], "learning": []}
    prev = {"frozen": None, "learning": None}

    # t=0 baseline (no games conditioned; learning == baseline)
    base_dist = champion_dist(simulate(structure, baseline, {}, {}, N, seed))
    for name in ("frozen", "learning"):
        _snapshot(traj, prev, name, -1, None, None, dict(base_dist))

    for i, g in enumerate(games):
        if g["kind"] == "group":
            groups[(g["home"], g["away"])] = g["result"]
        else:
            ko[(g["home"], g["away"])] = g["result"]
        learn.apply_match(g["home"], g["away"],
                          g["lam_obs"]["home"], g["lam_obs"]["away"])
        learn_ratings = {t: learn.rating(t) for t in baseline}
        for name, ratings in (("frozen", baseline), ("learning", learn_ratings)):
            dist = champion_dist(simulate(structure, ratings, groups, ko, N, seed))
            _snapshot(traj, prev, name, i, g["home"], g["away"], dist)
    return traj
