"""Generic Monte Carlo tournament simulator: a group stage (round-robin) plus a
single-elimination knockout, parameterized by a structure dict + Elo ratings +
played results. Format-agnostic (2022, 2026, or any synthetic bracket). Unplayed
group games are simulated from lambda_expected -> Poisson; knockout ties from Elo
win-probability. Produces per-team champion + stage-reached probabilities."""
import random

from learn import lambda_expected
from poisson_model import pois, MAX_G


def win_prob(r_a, r_b):
    """Elo win probability of A over B (knockout — no draws)."""
    return 1.0 / (1.0 + 10 ** (-(r_a - r_b) / 400.0))


def _sample_goals(lam, rng):
    """Sample a goal count from Poisson(lam) via the project's pmf."""
    r, acc = rng.random(), 0.0
    for k in range(MAX_G + 1):
        acc += pois(k, lam)
        if r <= acc:
            return k
    return MAX_G


def simulate_knockout(seeds, ratings, ko_results, rng):
    """seeds = flat list of teams in bracket order (length a power of two).
    Fold the single-elim tree. Returns {team: depth}: entrants have depth 1,
    each win adds 1, so the champion has depth 1 + n_rounds. Played ties use
    ko_results[(a, b)] = winner (either orientation)."""
    depth = {t: 1 for t in seeds}
    teams = list(seeds)
    while len(teams) > 1:
        nxt = []
        for i in range(0, len(teams), 2):
            a, b = teams[i], teams[i + 1]
            played = ko_results.get((a, b), ko_results.get((b, a)))
            if played in (a, b):
                w = played
            else:
                w = a if rng.random() < win_prob(ratings[a], ratings[b]) else b
            depth[w] += 1
            nxt.append(w)
        teams = nxt
    return depth


def group_standings(teams, fixtures, ratings, results, rng):
    """Rank a group. fixtures = [(home, away), ...]. A pair in results uses its
    (hg, ag); otherwise the scoreline is simulated from ratings. Returns the
    teams ordered by (points, goal difference, goals for), best first."""
    pts = {t: 0 for t in teams}
    gd = {t: 0 for t in teams}
    gf = {t: 0 for t in teams}
    for h, a in fixtures:
        if (h, a) in results:
            hg, ag = results[(h, a)]
        else:
            lh, la = lambda_expected(ratings[h], ratings[a])
            hg, ag = _sample_goals(lh, rng), _sample_goals(la, rng)
        gf[h] += hg
        gf[a] += ag
        gd[h] += hg - ag
        gd[a] += ag - hg
        if hg > ag:
            pts[h] += 3
        elif hg < ag:
            pts[a] += 3
        else:
            pts[h] += 1
            pts[a] += 1
    # stable sort: teams tied on (pts, gd, gf) keep group-list order -> reproducible
    return sorted(teams, key=lambda t: (pts[t], gd[t], gf[t]), reverse=True)


def simulate_once(structure, ratings, group_results, ko_results, rng):
    """One Monte Carlo run. Returns {team: depth}: 0 if eliminated in the group
    stage, else 1 + knockout wins (champion = 1 + n_rounds)."""
    standings = {
        g: group_standings(teams, structure["fixtures"][g],
                           ratings, group_results, rng)
        for g, teams in structure["groups"].items()
    }
    seeds = [standings[g][pos - 1] for (g, pos) in structure["bracket"]]
    depth = simulate_knockout(seeds, ratings, ko_results, rng)
    out = {t: 0 for teams in structure["groups"].values() for t in teams}
    out.update(depth)
    return out


def simulate(structure, ratings, group_results=None, ko_results=None,
             N=20000, seed=2026):
    """Run N tournaments. Returns {team: {"champion": p, "reached": {r: p}}}
    where reached[r] is P(reaching knockout round r), r = 1..n_rounds."""
    group_results = group_results or {}
    ko_results = ko_results or {}
    nb = len(structure["bracket"])
    assert nb & (nb - 1) == 0 and nb > 1, "bracket size must be a power of two"
    rng = random.Random(seed)
    teams = [t for ts in structure["groups"].values() for t in ts]
    n_rounds = nb.bit_length() - 1   # log2(bracket size)
    champ_depth = n_rounds + 1
    champ = {t: 0 for t in teams}
    reached = {t: {r: 0 for r in range(1, n_rounds + 1)} for t in teams}
    for _ in range(N):
        d = simulate_once(structure, ratings, group_results, ko_results, rng)
        for t, depth in d.items():
            if depth == champ_depth:
                champ[t] += 1
            for r in range(1, n_rounds + 1):
                if depth >= r:
                    reached[t][r] += 1
    return {
        t: {"champion": champ[t] / N,
            "reached": {r: reached[t][r] / N for r in range(1, n_rounds + 1)}}
        for t in teams
    }
