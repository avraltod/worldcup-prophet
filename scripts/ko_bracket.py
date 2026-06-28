"""Deterministic knockout bracket resolver. Reconstructs which two teams meet in
each KO match (73-104) from the recorded results, reusing condition.py's bracket
tables. Pure: no side effects, no network. Imports condition.py but never edits it."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from condition import GROUPS, ROW_MATCH, RATES, R32, R16, QF, SF, assign

GROUP_LETTERS = "ABCDEFGHIJKL"


def _standings(g_obs):
    """Return (pos, thirds) or (None, None).
    pos: {"<grp>1": team, "<grp>2": team}; thirds: {grp: (third_team, key_tuple)}.
    None if the group stage is incomplete or a 1st/2nd/3rd boundary tie is ambiguous."""
    pos, thirds = {}, {}
    for grp in GROUP_LETTERS:
        st = {}
        for row in GROUPS[grp]:
            m = ROW_MATCH[row]
            if m not in g_obs:
                return None, None                      # group stage incomplete
            _lh, _la, home, away = RATES[row]
            hg, ag = g_obs[m]
            for t, f, ag_ in ((home, hg, ag), (away, ag, hg)):
                s = st.setdefault(t, [0, 0, 0])
                s[0] += 3 if f > ag_ else (1 if f == ag_ else 0)
                s[1] += f - ag_
                s[2] += f
        order = sorted(st, key=lambda t: tuple(st[t]), reverse=True)
        keys = [tuple(st[t]) for t in order]
        if keys[0] == keys[1] or keys[1] == keys[2]:    # boundary tie -> ambiguous
            return None, None
        pos[f"{grp}1"], pos[f"{grp}2"] = order[0], order[1]
        thirds[grp] = (order[2], tuple(st[order[2]]))
    return pos, thirds


def _r32_slots(g_obs):
    """Return {slot_name: team} for all R32 slots, or None if unresolved."""
    pos, thirds = _standings(g_obs)
    if pos is None:
        return None
    rk = sorted(thirds, key=lambda g: thirds[g][1], reverse=True)
    keys = [thirds[g][1] for g in rk]
    if len(keys) >= 9 and keys[7] == keys[8]:           # 8th/9th third tie -> ambiguous
        return None
    random.seed(2026)
    am = assign(rk[:8]) or assign(rk[:7] + [rk[8]])
    if am is None:
        return None
    slots = dict(pos)
    for t_match, grp in am.items():
        slots[f"T{t_match}"] = thirds[grp][0]
    return slots


def resolve_ko_pairings(results_log):
    """Return {match#: frozenset({teamA, teamB})} for KO matches whose both teams
    are known. R32 needs complete group standings; later rounds need recorded winners."""
    g_obs = {int(k): v for k, v in results_log.get("group", {}).items()}
    W = {int(k): v for k, v in results_log.get("ko", {}).items()}
    pairings = {}

    slots = _r32_slots(g_obs) if len(g_obs) >= 72 else None
    if slots is not None:
        for m, (s1, s2) in R32.items():
            if s1 in slots and s2 in slots:
                pairings[m] = frozenset({slots[s1], slots[s2]})

    for tab in (R16, QF, SF):
        for m, (m1, m2) in tab.items():
            if m1 in W and m2 in W:
                pairings[m] = frozenset({W[m1], W[m2]})
    if 101 in W and 102 in W:
        pairings[104] = frozenset({W[101], W[102]})       # final (champion match)
    if 101 in pairings and 102 in pairings and 101 in W and 102 in W:
        l1, l2 = pairings[101] - {W[101]}, pairings[102] - {W[102]}
        if len(l1) == 1 and len(l2) == 1:
            pairings[103] = frozenset(l1 | l2)            # bronze final (not conditioned)
    return pairings
