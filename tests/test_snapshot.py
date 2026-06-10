import pytest
from snapshot import kl_divergence

def test_kl_zero_for_identical_distributions():
    p = {"a": 0.5, "b": 0.3, "c": 0.2}
    assert kl_divergence(p, p) == 0.0

def test_kl_positive_when_different():
    p = {"a": 0.7, "b": 0.3}
    q = {"a": 0.3, "b": 0.7}
    assert kl_divergence(p, q) > 0

def test_kl_one_bit_for_half_mass_move():
    # all mass on 'a' (was 0.5) -> KL = 1*log2(1/0.5) = 1 bit
    p = {"a": 1.0, "b": 0.0}
    q = {"a": 0.5, "b": 0.5}
    assert kl_divergence(p, q) == pytest.approx(1.0)

def test_kl_skips_zero_mass_terms_and_floors_q():
    # b has 0 prob in p -> contributes nothing; a-only term, q floored (no div0)
    p = {"a": 1.0, "b": 0.0}
    q = {"a": 1.0, "b": 0.0}
    assert kl_divergence(p, q) == 0.0
