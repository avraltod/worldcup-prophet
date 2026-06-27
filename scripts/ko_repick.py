"""EV-optimal full knockout entry on the real R32 bracket (friends' pool).

Derives the real 32-team R32 field from condition.realized_bracket, then
forward-propagates the EV-optimal advancer (per ko_match_ev) through R16, QF, SF,
Final, and the third-place playoff, producing one internally-consistent entry.
'Greedy by advance probability' is the reachability-optimal advancer choice for
the 'scored only if the projected matchup occurs' rule: advancing the stronger
team maximizes the chance later picks stay live. Run AFTER the group stage, once
REALIZED_THIRDS is pinned."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import condition as C
import ko_match_ev as kme

FINAL, THIRD = 104, 103


def real_r32_slots(results):
    """{'A1','A2','T74',...} -> team, from the fully-observed group results."""
    slots, _am = C.realized_bracket(results)
    return slots


def _pair(m, slots, winners):
    if m in C.R32:
        x, y = C.R32[m]
        return slots[x], slots[y]
    table = C.R16 if m in C.R16 else (C.QF if m in C.QF else C.SF)
    a, b = table[m]
    return winners[a], winners[b]


def _pick(home, away, eff):
    lh, la = kme.matchup_lambdas(home, away, eff)
    best = kme.match_ev(lh, la)
    adv = home if best["advancer"] == "home" else away
    loser = away if adv == home else home
    return {"home": home, "away": away, "score": best["score"],
            "advancer": adv, "loser": loser, "ev": best["ev"]}


def build_entry(results, eff=None):
    if eff is None:
        eff = kme.load_live_eff()      # Track B: all post-group-stage information
    slots = real_r32_slots(results)
    winners, picks = {}, {}
    for m in sorted(C.R32) + sorted(C.R16) + sorted(C.QF) + sorted(C.SF):
        home, away = _pair(m, slots, winners)
        picks[m] = _pick(home, away, eff)
        winners[m] = picks[m]["advancer"]
    picks[FINAL] = _pick(winners[101], winners[102], eff)
    picks[THIRD] = _pick(picks[101]["loser"], picks[102]["loser"], eff)
    return {"champion": picks[FINAL]["advancer"], "picks": picks, "eff": eff}
