import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import live_stats as ls

E1 = {"match": 1, "result": [2, 0], "failure_mode": None,
      "pre": {"pick": [2, 1]},
      "post": {"points": 1, "brier": 0.1655},
      "champ_top_full": {"Spain": 0.2711, "Argentina": 0.1815}}
E2 = {"match": 2, "result": [1, 1], "failure_mode": "systematic_rating_error",
      "pre": {"pick": [1, 1]},
      "post": {"points": 3, "brier": 0.40},
      "champ_top_full": {"Spain": 0.27, "Argentina": 0.18}}

def test_compute_aggregates():
    s = ls.compute([E1, E2], latest_champion={"Spain": 0.27, "Argentina": 0.18})
    assert s["documented"] == 2
    assert s["cum_points"] == 4
    assert round(s["mean_brier"], 4) == 0.2828      # (0.1655+0.40)/2
    assert round(s["exact_rate"], 4) == 0.5          # E2 pick == result
    assert s["failure_tally"]["systematic_rating_error"] == 1
    assert s["champ_top"][0] == ["Spain", 0.27]

def test_render_macros_are_consistent():
    s = ls.compute([E1, E2], latest_champion={"Spain": 0.27})
    tex = ls.render_macros(s)
    assert r"\def\liveCumPoints{4}" in tex
    assert r"\def\liveMeanBrier{0.28}" in tex
    assert r"\def\liveDocumented{2}" in tex
    assert r"\def\liveRealVsEVDelta{+0}" in tex
    assert r"\def\liveReEvDelta{" not in tex       # old name must not appear


def test_total_bits_and_bits_of_max_in_compute():
    entries = [
        {"match": 1, "result": [2, 0], "failure_mode": None,
         "pre": {"pick": [2, 1]},
         "post": {"points": 1, "brier": 0.17, "info_bits": 0.3}},
        {"match": 2, "result": [1, 1], "failure_mode": None,
         "pre": {"pick": [1, 1]},
         "post": {"points": 3, "brier": 0.40, "info_bits": 0.2}},
    ]
    s = ls.compute(entries, {"Spain": 0.27})
    assert abs(s["total_bits"] - 0.5) < 1e-9
    assert abs(s["bits_of_max"] - (0.5 / 6.6 * 100)) < 0.01


def test_render_macros_new_fields():
    entries = [{"match": 1, "result": [2, 0], "failure_mode": None,
                "pre": {"pick": [2, 1]},
                "post": {"points": 1, "brier": 0.17, "info_bits": 0.08}}]
    s = ls.compute(entries, {"Spain": 0.27, "Argentina": 0.18})
    s["champ_b_top"] = [("Spain", 0.28), ("Argentina", 0.18), ("France", 0.14)]
    tex = ls.render_macros(s)
    assert r"\def\liveTotalBits{0.08}" in tex
    assert r"\def\liveBitsOfMax{1.2}" in tex
    assert r"\def\liveTrackBRevision{Spain 28.0\%" in tex
    assert "Argentina 18.0\\%" in tex


# ---------------- live-edition macros (version line, abstract, update log) ---

E_FULL = {"match": 2, "fixture": "South Korea v Czechia", "result": [2, 1],
          "kickoff": "2026-06-12T02:00:00Z", "failure_mode": None,
          "pre": {"pick": [1, 1]}, "post": {"points": 0, "brier": 0.613}}


def test_version_line_pre_kickoff_when_nothing_documented():
    s = ls.compute([], latest_champion={"Spain": 0.27})
    assert ls._version_line(s) == r"Pre-kickoff version, \today"
    tex = ls.render_macros(s)
    assert r"\def\liveAbstractRevision{}" in tex      # degrades to empty
    assert r"\def\liveUpdateLog{}" in tex


def test_version_line_self_describes_the_edition():
    s = ls.compute([E_FULL], latest_champion={"Spain": 0.27})
    line = ls._version_line(s)
    assert line == ("Live edition --- after match 2, "
                    "South Korea 2--1 Czechia (12 June 2026)")


def test_abstract_revision_grammar_and_names():
    s = ls.compute([E_FULL], latest_champion={"Spain": 0.27})
    s["champ_now_top"] = [("Spain", 0.269), ("Argentina", 0.179), ("France", 0.143)]
    one = ls._abstract_revision(s)
    assert "the 1 result played" in one                # singular
    assert "Spain at 26.9 percent" in one
    assert ", and France at 14.3." in one              # Oxford 'and' before last
    s2 = ls.compute([E_FULL, dict(E_FULL, match=3)], latest_champion={"Spain": 0.27})
    s2["champ_now_top"] = s["champ_now_top"]
    assert "the 2 results played" in ls._abstract_revision(s2)


def test_abstract_revision_empty_without_conditional_forecast():
    s = ls.compute([E_FULL], latest_champion={"Spain": 0.27})
    assert ls._abstract_revision(s) == ""              # no champ_now_top passed


def test_update_log_names_every_result_and_the_lock_tag():
    s = ls.compute([E_FULL], latest_champion={"Spain": 0.27})
    log = ls._update_log(s) if hasattr(ls, "_update_log") else ""
    s["entries"] = [E_FULL]
    log = ls._update_log(s)
    assert "M2 South Korea 2--1 Czechia" in log
    assert "prereg-2026" in log


# -------------------- live edition number macro ---

def _s(n=4):
    entries = [{"match": i, "result": [2, 0], "pre": {"pick": [2, 1]},
                "post": {"points": 1, "brier": 0.2, "info_bits": 0.01},
                "fixture": "A v B", "kickoff": "2026-06-11T19:00:00Z",
                "failure_mode": None}
               for i in range(1, n+1)]
    s = ls.compute(entries, {"Spain": 0.27})
    s["entries"] = entries
    return s


def test_live_edition_num_macro_present():
    tex = ls.render_macros(_s(4))
    assert r"\def\liveEditionNum{004}" in tex


def test_live_edition_num_zero_when_no_entries():
    s = ls.compute([], {})
    s["entries"] = []
    tex = ls.render_macros(s)
    assert r"\def\liveEditionNum{000}" in tex
