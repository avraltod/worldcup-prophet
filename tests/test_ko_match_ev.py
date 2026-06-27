import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ko_match_ev as kme


def test_advance_probs_sum_to_one():
    p_home, p_away = kme.advance_probs(1.4, 1.1)
    assert abs((p_home + p_away) - 1.0) < 1e-9


def test_even_match_is_coin_flip_on_penalties():
    p_home, p_away = kme.advance_probs(1.2, 1.2)
    assert abs(p_home - 0.5) < 1e-9 and abs(p_away - 0.5) < 1e-9


def test_heavy_favorite_advances_and_picks_decisive_win():
    p_home, _ = kme.advance_probs(2.2, 0.3)
    assert p_home > 0.9
    best = kme.match_ev(2.2, 0.3)
    h, a = best["score"]
    assert h > a and best["advancer"] == "home"
    assert 0.0 < best["ev"] <= 4.0


def test_even_match_picks_higher_advance_team_on_a_draw():
    best = kme.match_ev(1.35, 1.15)
    h, a = best["score"]
    if h == a:
        assert best["advancer"] == "home"
    assert best["adv_prob"] >= 0.5


def test_matchup_lambdas_from_eff():
    eff = {"Strong": 2100.0, "Weak": 1500.0}
    lh, la = kme.matchup_lambdas("Strong", "Weak", eff)
    assert lh > la
