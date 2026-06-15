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


def test_champdist_fig_creates_file(tmp_path):
    frozen = {"Spain": {"champion": 0.269}, "Argentina": {"champion": 0.179},
              "France": {"champion": 0.143}}
    now = {"Spain": {"champion": 0.270}, "Argentina": {"champion": 0.180},
           "France": {"champion": 0.142}}
    out = tmp_path / "fig_live_champdist.pdf"
    mlf.champdist_fig(frozen, now, str(out))
    assert out.exists()
