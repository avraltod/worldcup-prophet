"""Per-knockout-match EV under the pool rule.

Points per KO match = [90' regulation score tier: 3 exact / 2 goal-difference /
1 result] + [+1 if the predicted advancing team is correct]. ET and penalty
SCORES are unscored; they only decide who advances. A 90' draw prediction lets
the advancer be chosen freely; a decisive 90' prediction forces the advancer to
the predicted winner. We pick the (90' score, advancer) maximizing total EV.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from poisson_model import pois, MAX_G
from ev321 import ev_321
from learn import lambda_expected


def _draw_prob(lh, la):
    return sum(pois(k, lh) * pois(k, la) for k in range(MAX_G + 1))


def _home_win_prob(lh, la):
    return sum(pois(i, lh) * pois(j, la)
               for i in range(MAX_G + 1) for j in range(MAX_G + 1) if i > j)


def advance_probs(lh, la, q_home=0.5):
    """(P(home advances), P(away advances)) via 90' -> extra time (lambda/3) ->
    penalties. q_home is the home team's shootout win prob (default 0.5: prior
    shootout records carry no predictive signal).

    Both sides are computed from their own cascade formula and then normalized
    so that truncated Poisson sums (capped at MAX_G) do not break the symmetry
    guarantee: advance_probs(l, l, 0.5) returns exactly (0.5, 0.5)."""
    pw90 = _home_win_prob(lh, la)
    pa90 = _home_win_prob(la, lh)   # symmetric: swap rates
    pd90 = _draw_prob(lh, la)
    eh, ea = lh / 3.0, la / 3.0    # 30 extra-time minutes -> a third of the rate
    pwET = _home_win_prob(eh, ea)
    paET = _home_win_prob(ea, eh)
    pdET = _draw_prob(eh, ea)
    p_home_raw = pw90 + pd90 * (pwET + pdET * q_home)
    p_away_raw = pa90 + pd90 * (paET + pdET * (1.0 - q_home))
    total = p_home_raw + p_away_raw
    return p_home_raw / total, p_away_raw / total


def match_ev(lh, la, q_home=0.5):
    """Best {score, advancer, ev, score_ev, adv_prob} for a matchup whose 90'
    Poisson means are (lh, la). advancer is 'home' or 'away'. Exhaustive over the
    0..MAX_G x 0..MAX_G score grid."""
    p_home, p_away = advance_probs(lh, la, q_home)
    best = None
    for h in range(MAX_G + 1):
        for a in range(MAX_G + 1):
            score_ev = ev_321(h, a, lh, la)
            if h > a:
                adv, adv_p = "home", p_home
            elif h < a:
                adv, adv_p = "away", p_away
            else:
                adv, adv_p = ("home", p_home) if p_home >= p_away else ("away", p_away)
            ev = score_ev + adv_p
            if best is None or ev > best["ev"]:
                best = {"score": (h, a), "advancer": adv, "ev": ev,
                        "score_ev": score_ev, "adv_prob": adv_p}
    return best


def load_live_eff():
    """Track B effective Elo for every team: live Elo + injuries + lineups +
    learned drift (all information available after the group games). No frozen
    host bonus — host edge is already inside the live ratings."""
    import live_state as ls
    return ls.build_eff_elo(ls.load_state(), ls.load_live_inputs())


def matchup_lambdas(team_home, team_away, eff):
    """90' Poisson means for a KO matchup from Track B effective Elo `eff`."""
    return lambda_expected(eff[team_home], eff[team_away])
