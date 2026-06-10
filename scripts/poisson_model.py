"""Poisson scoreline model: odds-implied probabilities -> modal exact score.

Given margin-stripped (p_home, p_draw, p_away) for a match, find the
Poisson goal-rate pair (lh, la) that best reproduces those outcome
probabilities, then return the most likely exact scoreline CONDITIONAL on
the most likely outcome (so the predicted score always agrees with the
predicted result -- maximizes expected points when exact score > result).
"""
import math
from functools import lru_cache

MAX_G = 8  # goal cap for probability grids


def pois(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


@lru_cache(maxsize=None)
def outcome_probs(lh, la):
    """P(home win), P(draw), P(away win) for Poisson rates lh, la."""
    ph = pd = pa = 0.0
    for i in range(MAX_G + 1):
        for j in range(MAX_G + 1):
            p = pois(i, lh) * pois(j, la)
            if i > j:
                ph += p
            elif i == j:
                pd += p
            else:
                pa += p
    return ph, pd, pa


def fit_rates(p_home, p_draw, p_away, total_goals_range=(1.6, 3.4)):
    """Grid-search (lh, la) minimizing squared error vs target outcome probs.

    World Cup group games average ~2.5-2.7 total goals; we let total goals
    float inside a sane band so lopsided matches can score more.
    """
    best, best_err = (1.35, 1.15), float("inf")
    steps = [round(0.05 * k, 2) for k in range(2, 71)]  # 0.10 .. 3.50
    for lh in steps:
        for la in steps:
            t = lh + la
            if not (total_goals_range[0] <= t <= total_goals_range[1]):
                continue
            ph, pd, pa = outcome_probs(lh, la)
            err = (ph - p_home) ** 2 + (pd - p_draw) ** 2 + (pa - p_away) ** 2
            if err < best_err:
                best, best_err = (lh, la), err
    return best


def modal_score(p_home, p_draw, p_away):
    """Most likely exact score conditional on the most likely outcome.

    Returns (home_goals, away_goals, info_dict).
    """
    lh, la = fit_rates(p_home, p_draw, p_away)
    outcome = max((("H", p_home), ("D", p_draw), ("A", p_away)), key=lambda x: x[1])[0]
    best_sc, best_p = (1, 1), -1.0
    for i in range(MAX_G + 1):
        for j in range(MAX_G + 1):
            ok = (outcome == "H" and i > j) or (outcome == "D" and i == j) \
                or (outcome == "A" and i < j)
            if not ok:
                continue
            p = pois(i, lh) * pois(j, la)
            if p > best_p:
                best_sc, best_p = (i, j), p
    info = {"lh": lh, "la": la, "outcome": outcome, "p_score": round(best_p, 4)}
    return best_sc[0], best_sc[1], info


if __name__ == "__main__":
    # sanity checks
    tests = [
        ("heavy favorite", 0.80, 0.13, 0.07),
        ("moderate favorite", 0.55, 0.25, 0.20),
        ("coin flip", 0.34, 0.32, 0.34),
        ("slight underdog home", 0.25, 0.28, 0.47),
    ]
    for name, ph, pd, pa in tests:
        h, a, info = modal_score(ph, pd, pa)
        print(f"{name}: {h}-{a}  {info}")
