"""Most-likely bracket: fill the submitted bracket structure with the team most
likely to occupy each position rather than the locked pick.

The submitted bracket (make_bracket_tikz: SEED, LEFT_R32, ...) places each
pre-registered pick at a position with a group+finishing-place identity (SEED,
e.g. "Turkey": "D2"). Here every R32-entry position is re-filled with the team
most likely to occupy it under a forecast `probs` ({team: {first, second,
third_adv, champion, ...}} as returned by condition.conditional_probs): the
argmax over that group's four teams of the relevant finishing-place probability,
assigned greedily so a group's 1st/2nd/3rd are distinct. The box value for an
entry slot is that occupancy probability (P reach this slot).

Rounds past R32 are an Elo most-likely PATH: the R32 field is propagated by a
caller-supplied head-to-head `winner(a, b, late)` (Track A: condition.rating;
Track B: live learn ratings). Deeper box values are P(champion). At the KO
cutover (~27 June, condition.REALIZED_THIRDS pinned) these can upgrade to exact
per-node occupancy; this module renders the group-stage view.

Pure logic, no matplotlib — the renderer lives in make_live_figures.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import make_bracket_tikz as bt   # SEED, LEFT_R32/R16/QF/SF, RIGHT_*, CHAMPION

# finishing place (SEED digit) -> key in conditional_probs output
PLACE_KEY = {1: "first", 2: "second", 3: "third_adv"}


def group_rosters(expectations):
    """{group letter: sorted [team, ...]} from match_expectations entries."""
    g = {}
    for e in expectations:
        g.setdefault(e["group"], set()).update([e["home"], e["away"]])
    return {k: sorted(v) for k, v in g.items()}


def place_occupants(probs, rosters):
    """{(group, place): (team, prob)} most-likely occupant of every group
    finishing position present in the submitted bracket (SEED). Greedy within a
    group so 1st/2nd/3rd are distinct: place 1 first, then 2, then 3."""
    needed = {}                                  # group -> set of places
    for ident in bt.SEED.values():
        needed.setdefault(ident[0], set()).add(int(ident[1]))
    out = {}
    for grp, places in needed.items():
        teams = rosters.get(grp, [])
        taken = set()
        for place in sorted(places):             # 1, then 2, then 3
            key = PLACE_KEY[place]
            cand = [t for t in teams if t not in taken] or list(teams)
            # deterministic: highest prob, ties broken by name
            best = max(cand, key=lambda t: (probs.get(t, {}).get(key, 0.0), t))
            out[(grp, place)] = (best, probs.get(best, {}).get(key, 0.0))
            taken.add(best)
    return out


def _occ(ident, occ):
    """(team, value) for a SEED identity like 'D2' from place_occupants."""
    return occ[(ident[0], int(ident[1]))]


def build(probs, rosters, winner):
    """Most-likely bracket structure for the renderer. `winner(a, b, late)`
    returns the head-to-head most-likely advancer. Mirrors the submitted bracket
    geometry (8/4/2/1 per half)."""
    occ = place_occupants(probs, rosters)

    def half(r32_pairs):
        # r32_pairs: list of 8 (home, away, _submitted_winner) from bt.LEFT/RIGHT_R32
        r32 = []                                 # (mlh, mla, mlw, vh, va)
        winners = []
        for home, away, _ in r32_pairs:
            mlh, vh = _occ(bt.SEED[home], occ)
            mla, va = _occ(bt.SEED[away], occ)
            w = winner(mlh, mla, False)
            r32.append((mlh, mla, w, vh, va))
            winners.append(w)
        r16 = [winner(winners[2 * k], winners[2 * k + 1], False) for k in range(4)]
        qf = [winner(r16[2 * k], r16[2 * k + 1], True) for k in range(2)]
        sf = winner(qf[0], qf[1], True)
        return {"R32": r32, "R16": r16, "QF": qf, "SF": sf}

    left = half(bt.LEFT_R32)
    right = half(bt.RIGHT_R32)
    champion = winner(left["SF"], right["SF"], True)
    return {"left": left, "right": right, "champion": champion}


def rating_winner(rating_of):
    """winner(a, b, late) picking the higher rating_of(team, late); ties -> name."""
    def w(a, b, late):
        ra, rb = rating_of(a, late), rating_of(b, late)
        return a if (ra, a) >= (rb, b) else b
    return w
