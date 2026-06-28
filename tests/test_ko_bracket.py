import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ko_bracket as kb
from fixtures import GROUP_FIXTURES, ROW_MATCH


def _complete_group_results():
    """A deterministic, boundary-tie-free set of all 72 group results.
    Each team gets a unique strength; the stronger team wins by a margin that
    varies with the strength pair, so points AND goal-diff/goals-for are distinct
    within groups and across third-placed teams. If a boundary tie ever appears
    (resolver returns < 16 R32 pairings), perturb the margin formula below."""
    teams = []
    for r, g, h, a in GROUP_FIXTURES:
        for t in (h, a):
            if t not in teams:
                teams.append(t)
    strength = {t: i for i, t in enumerate(teams)}
    g_obs = {}
    for r, g, h, a in GROUP_FIXTURES:
        m = ROW_MATCH[r]
        sh, sa = strength[h], strength[a]
        margin = 1 + ((sh * sa + sh) % 7)        # 1..5, varies GD/GF
        g_obs[str(m)] = [margin, 0] if sh > sa else [0, margin]
    return g_obs


def test_resolver_yields_full_R32_with_32_distinct_teams():
    log = {"group": _complete_group_results(), "ko": {}}
    pairings = kb.resolve_ko_pairings(log)
    r32 = {m: p for m, p in pairings.items() if 73 <= m <= 88}
    assert len(r32) == 16, f"expected 16 R32 pairings, got {len(r32)}"
    teams = [t for p in r32.values() for t in p]
    assert len(teams) == 32 and len(set(teams)) == 32  # no team appears twice

def test_resolver_is_deterministic():
    log = {"group": _complete_group_results(), "ko": {}}
    assert kb.resolve_ko_pairings(log) == kb.resolve_ko_pairings(log)

def test_incomplete_group_stage_yields_no_R32():
    log = {"group": {"1": [2, 1]}, "ko": {}}   # only 1 of 72
    pairings = kb.resolve_ko_pairings(log)
    assert all(m > 88 for m in pairings)        # no R32 pairings

def test_recorded_ko_winners_propagate_to_next_round():
    log = {"group": _complete_group_results(), "ko": {}}
    base = kb.resolve_ko_pairings(log)
    a74, a77 = sorted(base[74]), sorted(base[77])
    log["ko"] = {"74": a74[0], "77": a77[0]}
    p = kb.resolve_ko_pairings(log)
    assert p[89] == frozenset({a74[0], a77[0]})
