"""Tests for the live_rates= parameter in conditional_probs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import condition as cond


def test_live_rates_none_is_backward_compatible():
    results = {"group": {}, "ko": {}}
    p1 = cond.conditional_probs(results, N=500, seed=42)
    p2 = cond.conditional_probs(results, N=500, seed=42, live_rates=None)
    assert p1 == p2


def test_live_rates_empty_dict_is_backward_compatible():
    results = {"group": {}, "ko": {}}
    p1 = cond.conditional_probs(results, N=500, seed=42)
    p2 = cond.conditional_probs(results, N=500, seed=42, live_rates={})
    assert p1 == p2


def test_live_rates_override_shifts_group_probs():
    """Extreme live_rates for one match should shift home team's champion probability."""
    row = cond.GROUPS["A"][0]
    home = cond.RATES[row][2]
    results = {"group": {}, "ko": {}}
    baseline = {t: cond.ELO[t] + cond.ADJ.get(t, 0) for t in cond.ELO}

    p_base = cond.conditional_probs(results, N=1000, seed=42, ratings=baseline)
    live = {row: [10.0, 0.1]}
    p_live = cond.conditional_probs(results, N=1000, seed=42,
                                     ratings=baseline, live_rates=live)

    assert p_live[home]["champion"] > p_base[home]["champion"]


def test_observed_result_takes_priority_over_live_rates():
    """A result already in results["group"] must override live_rates for that match.
    We verify this by checking that adding live_rates for an already-observed match
    produces the same output as not providing live_rates at all — the observed result
    fires first and the live_rates branch is never reached for that row."""
    row = cond.GROUPS["A"][0]
    m = cond.ROW_MATCH[row]
    results = {"group": {str(m): [0, 5]}, "ko": {}}
    baseline = {t: cond.ELO[t] + cond.ADJ.get(t, 0) for t in cond.ELO}

    # Without live_rates for this row
    p_no_live = cond.conditional_probs(results, N=500, seed=42, ratings=baseline)
    # live_rates says home dominates for the same match, but 0-5 result is already observed
    live = {row: [10.0, 0.1]}
    p_with_live = cond.conditional_probs(results, N=500, seed=42,
                                          ratings=baseline, live_rates=live)

    # The two calls must be identical: the observed result takes priority and the
    # live_rates branch for this row is never executed (same seed => same outcomes)
    assert p_no_live == p_with_live
