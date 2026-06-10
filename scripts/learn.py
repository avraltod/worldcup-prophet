"""Track B learning engine: turn observed performance (lambda_obs) into a
bounded, regularized update of each team's Elo strength. k=0 reproduces the
frozen track. Reuses the project's existing Elo->prob->lambda model."""
import math
from functools import lru_cache

from poisson_model import fit_rates


@lru_cache(maxsize=None)
def _lambda_for_diff(d):
    """Expected goals for a rating difference d = r_home - r_away. Cached: the
    same d recurs across every Monte Carlo iteration, and fit_rates is a grid
    search, so memoizing makes the simulator orders of magnitude faster."""
    e0 = 1.0 / (1.0 + 10 ** (-d / 400.0))
    pd = 0.30 * math.exp(-abs(d) / 700.0)
    ph = max(0.01, e0 - pd / 2.0)
    pa = max(0.01, 1.0 - ph - pd)
    s = ph + pd + pa
    return fit_rates(ph / s, pd / s, pa / s)


def lambda_expected(r_home, r_away):
    """Two ratings -> (lam_home, lam_away) expected goals, via the same Elo
    win-expectancy + draw model the backtest uses, then fit_rates. Depends only
    on the rating difference, rounded to 1 Elo point for caching."""
    return _lambda_for_diff(round(r_home - r_away))


def net_surprise(lam_obs_for, lam_exp_for, lam_obs_against, lam_exp_against):
    """Zero-sum performance surprise for the 'for' team: how much it out-xG'd
    expectation in attack, minus how much it leaked in defense."""
    return (lam_obs_for - lam_exp_for) - (lam_obs_against - lam_exp_against)


def update_drift(drift, surprise, k, decay, bound):
    """Regularized online step: decay the accumulated drift toward baseline (0),
    then add the learning step k*surprise, clipped to +/- bound."""
    step = max(-bound, min(bound, k * surprise))
    return decay * drift + step


class LearningTrack:
    """Holds baseline Elo ratings plus a per-team accumulated drift. Each match
    nudges the two teams' drifts symmetrically (zero-sum). The current strength
    of a team is baseline + drift. k is the swept knob (k=0 => frozen track)."""

    def __init__(self, baseline, k=50.0, decay=0.95, bound=75.0):  # k=50: 2018+2022 k-sweep compromise
        self.baseline = dict(baseline)
        self.drift = {t: 0.0 for t in baseline}
        self.k = k
        self.decay = decay
        self.bound = bound

    def rating(self, team):
        # team must be in baseline (all tournament teams are seeded up front)
        return self.baseline[team] + self.drift[team]

    def apply_match(self, home, away, lam_obs_home, lam_obs_away):
        """Update both teams' drift from one finished match's observed goals."""
        lam_exp_home, lam_exp_away = lambda_expected(self.rating(home),
                                                     self.rating(away))
        s_home = net_surprise(lam_obs_home, lam_exp_home,
                              lam_obs_away, lam_exp_away)
        for team, s in ((home, s_home), (away, -s_home)):
            self.drift[team] = update_drift(self.drift[team], s,
                                            self.k, self.decay, self.bound)
