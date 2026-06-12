import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import render_evolution as re_

SAMPLE = ("FROZEN ABOVE\n"
          "% LIVE-EVOLUTION-TABLE:START\n"
          "old table\n"
          "% LIVE-EVOLUTION-TABLE:END\n"
          "FROZEN BELOW\n")

ENTRIES = [
    {"match": 1, "fixture": "Mexico v South Africa", "result": [2, 0],
     "failure_mode": None,
     "pre": {"pick": [1, 0]},
     "post": {"points": 1, "brier": 0.1655, "info_bits": 0.0011},
     "interpretation": "A likely home win arrived; the title race barely moved."},
]

def test_replace_markers_only_touches_the_block():
    out = re_.replace_markers(SAMPLE, "LIVE-EVOLUTION-TABLE", "NEW\nROWS")
    assert "FROZEN ABOVE" in out and "FROZEN BELOW" in out
    assert "old table" not in out
    assert "NEW\nROWS" in out

def test_missing_marker_raises():
    try:
        re_.replace_markers("no markers here", "LIVE-EVOLUTION-TABLE", "x")
        assert False, "expected ValueError"
    except ValueError:
        pass

def test_frozen_hash_ignores_marker_contents():
    h1 = re_.frozen_hash(SAMPLE)
    changed = re_.replace_markers(SAMPLE, "LIVE-EVOLUTION-TABLE", "totally different")
    assert re_.frozen_hash(changed) == h1     # frozen text unchanged

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
       "rows": [("Mexico", 3, 2), ("South Korea", 3, 1),
                ("Czechia", 0, -1), ("South Africa", 0, -2)]}]


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


FULL = ("HEAD\n"
        "% LIVE-EVOLUTION-TABLE:START\nx\n% LIVE-EVOLUTION-TABLE:END\n"
        "% LIVE-EVOLUTION-NARRATIVE:START\nx\n% LIVE-EVOLUTION-NARRATIVE:END\n"
        "% LIVE-EVOLUTION-TRAJFIG:START\nx\n% LIVE-EVOLUTION-TRAJFIG:END\n"
        "% LIVE-EVOLUTION-DIVERGENCE:START\nx\n% LIVE-EVOLUTION-DIVERGENCE:END\n"
        "% LIVE-EVOLUTION-CHAMPTABLE:START\nx\n% LIVE-EVOLUTION-CHAMPTABLE:END\n"
        "TAIL\n")


def test_render_paper_fills_all_five_regions_and_frozen_hash_is_invariant():
    h0 = re_.frozen_hash(FULL)
    out = re_.render_paper(FULL, ENTRIES, frozen=FROZEN, now=NOW,
                           group_state=GS, live_fig=True)
    assert re_.frozen_hash(out) == h0
    assert "HEAD" in out and "TAIL" in out
    for token in ("longtable", "fig_trajectory_live", "Champion (lock)",
                  "diverges from the locked baseline"):
        assert token in out, token
