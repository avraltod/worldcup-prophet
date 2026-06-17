import matplotlib
matplotlib.use("Agg")

import make_live_figures as mlf


def _stages(c):
    return {t: {"advance_KO": 0.5 + i * 0.01, "champion": c,
                "first": 0.3, "second": 0.15, "third_adv": 0.05 + i * 0.01}
            for i, t in enumerate(["Spain", "Argentina", "France", "Mexico"])}


def test_group_qual_fig(tmp_path):
    # stacked Win/2nd/3rd/Out grid for one track; now[team] has the decomposition
    out = tmp_path / "q.pdf"
    mlf.group_qual_fig(_stages(0.25),
                       {"A": ["Spain", "Argentina"], "B": ["France", "Mexico"]}, out)
    assert out.exists() and out.stat().st_size > 0


def test_two_track_fig(tmp_path):
    out = tmp_path / "t.pdf"
    history = [{"match": 1,
                "frozen_top": {"Spain": 0.27, "France": 0.14},
                "learning_top": {"Spain": 0.28, "France": 0.13}},
               {"match": 2,
                "frozen_top": {"Spain": 0.27, "France": 0.14},
                "learning_top": {"Spain": 0.29, "France": 0.12}}]
    mlf.two_track_fig(history, out)
    assert out.exists() and out.stat().st_size > 0


def test_market_fig_creates_file_with_many_teams(tmp_path):
    # 14 teams: market_fig caps at the top 12 by Track A without erroring.
    names = ["Spain", "Argentina", "France", "Portugal", "England", "Brazil",
             "Netherlands", "Germany", "Norway", "Ecuador", "Croatia",
             "Colombia", "Belgium", "Uruguay"]
    track_a = {t: {"champion": 0.27 - 0.018 * i} for i, t in enumerate(names)}
    frozen = {t: {"champion": 0.27 - 0.018 * i} for i, t in enumerate(names)}
    track_b = {t: 0.26 - 0.018 * i for i, t in enumerate(names)}
    market = {t: 0.16 - 0.010 * i for i, t in enumerate(names)}
    out = tmp_path / "fig_live_market.pdf"
    mlf.market_fig(frozen, track_a, track_b, market, str(out))
    assert out.exists() and out.stat().st_size > 0


def test_market_fig_handles_missing_track_b_and_market(tmp_path):
    track_a = {"Spain": {"champion": 0.27}, "France": {"champion": 0.14}}
    frozen = {"Spain": {"champion": 0.27}, "France": {"champion": 0.14}}
    out = tmp_path / "fig_live_market.pdf"
    mlf.market_fig(frozen, track_a, None, {}, str(out))
    assert out.exists() and out.stat().st_size > 0
