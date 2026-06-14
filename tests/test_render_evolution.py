import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import render_evolution as re_

ENTRIES = [
    {"match": 1, "fixture": "Mexico v South Africa", "result": [2, 0],
     "failure_mode": None,
     "pre": {"pick": [1, 0]},
     "post": {"points": 1, "brier": 0.1655, "info_bits": 0.0011},
     "interpretation": "A likely home win arrived; the title race barely moved."},
]

def test_ledger_table_has_one_row_per_entry():
    tex = re_.ledger_table(ENTRIES)
    assert "\\begin{longtable}" in tex and "\\end{longtable}" in tex
    assert "\\endhead" in tex                       # header repeats across pages
    assert "Mexico v South Africa" in tex
    assert "2--0" in tex          # result rendered with en-dash
    assert "1--0" in tex          # pick rendered with en-dash
    assert "0.001" in tex         # info_bits to 3dp
    assert tex.count(r"\\") >= 2  # header row + at least one data row

def test_ledger_table_empty_is_a_placeholder_not_broken_latex():
    tex = re_.ledger_table([])
    assert "longtable" not in tex
    assert "&" not in tex          # no bare alignment chars
    assert "No matches documented yet" in tex


# ---------------- live-edition additions (divergence, champ table, trajfig) --

FROZEN = {
    "Spain":       {"champion": .269, "final": .388, "SF": .517, "advance_KO": .989},
    "Argentina":   {"champion": .181, "final": .301, "SF": .431, "advance_KO": .989},
    "France":      {"champion": .143, "final": .246, "SF": .433, "advance_KO": .985},
    "South Korea": {"champion": .001, "final": .004, "SF": .013, "advance_KO": .662},
    "Czechia":     {"champion": .001, "final": .003, "SF": .010, "advance_KO": .683},
}
NOW = {
    "Spain":       {"champion": .269, "final": .388, "SF": .517, "advance_KO": .989},
    "Argentina":   {"champion": .179, "final": .301, "SF": .431, "advance_KO": .989},
    "France":      {"champion": .143, "final": .246, "SF": .433, "advance_KO": .985},
    "South Korea": {"champion": .001, "final": .004, "SF": .013, "advance_KO": .925},
    "Czechia":     {"champion": .000, "final": .002, "SF": .008, "advance_KO": .508},
}
GS = [{"group": "A", "played": 2, "total": 6,
       "rows": [{"team": "Mexico",       "P": 2, "W": 1, "D": 0, "L": 0, "GF": 3, "GA": 1, "Pts": 3},
                {"team": "South Korea",  "P": 2, "W": 1, "D": 0, "L": 0, "GF": 3, "GA": 2, "Pts": 3},
                {"team": "Czechia",      "P": 2, "W": 0, "D": 0, "L": 1, "GF": 1, "GA": 2, "Pts": 0},
                {"team": "South Africa", "P": 2, "W": 0, "D": 0, "L": 1, "GF": 1, "GA": 3, "Pts": 0}]}]


def test_divergence_lists_movers_and_pins_frozen_column():
    tex = re_.divergence_section(FROZEN, NOW, ENTRIES, GS)
    assert "South Korea" in tex and "Czechia" in tex      # 3pp advance movers
    assert "$+26.3$" in tex and "$-17.5$" in tex
    assert "66.2" in tex                                  # frozen value printed
    assert "Group A" in tex and "Mexico 3 pts (+2)" in tex
    assert tex.count("\\begin{longtable}") == tex.count("\\end{longtable}") == 1


def test_divergence_empty_is_placeholder():
    tex = re_.divergence_section(FROZEN, NOW, [], GS)
    assert "longtable" not in tex and "equals the baseline" in tex


def test_champ_table_ranks_by_now_and_keeps_lock_column():
    tex = re_.champ_table(FROZEN, NOW, 2)
    assert "Champion (lock)" in tex and "Champion (now)" in tex
    assert "label{tab:champ}" in tex
    assert tex.index("Spain") < tex.index("Argentina") < tex.index("France")
    assert "26.9\\%" in tex                               # lock column value
    assert "conditioned on the 2 results" in tex
    assert tex.count("\\begin{table}") == tex.count("\\end{table}") == 1


def test_trajfig_falls_back_to_demo():
    assert "fig_trajectory_demo" in re_.trajfig([])
    assert "fig_trajectory_demo" in re_.trajfig(ENTRIES, live_fig=False)
    live = re_.trajfig(ENTRIES, live_fig=True)
    assert "fig_trajectory_live" in live
    assert "label{fig:trajectory}" in live                # label preserved
    assert "1 of 104" in live


CHAMPION_B = {
    "Spain":     0.271,
    "Argentina": 0.191,
    "France":    0.138,
}

def test_champ_table_with_champion_b_adds_track_b_columns():
    tex = re_.champ_table(FROZEN, NOW, 2, champion_b=CHAMPION_B)
    assert "Track A" in tex
    assert "Track B" in tex
    assert r"\Delta" in tex
    assert "27.1\\%" in tex   # Spain Track B
    assert "+0.2" in tex      # Spain delta: 27.1 - 26.9 = +0.2
    assert "+1.2" in tex      # Argentina delta: 19.1 - 17.9 = +1.2
    assert r"\label{tab:champ}" in tex
    assert tex.count(r"\begin{table}") == tex.count(r"\end{table}") == 1

def test_champ_table_without_champion_b_renders_as_before():
    tex = re_.champ_table(FROZEN, NOW, 2)
    assert "Track B" not in tex
    assert "Champion (now)" in tex
    assert "Champion (lock)" in tex
    assert r"\label{tab:champ}" in tex
