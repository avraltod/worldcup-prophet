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

def test_ledger_table_g_column_and_issue_order():
    # Leading G column, ordered by issue order (GXXX) not match number, and the
    # Info (bits) column (which absorbs the old 'information revealed' table).
    ents = [
        {"match": 1, "fixture": "Mexico v South Africa", "failure_mode": None,
         "pre": {"pick": [1, 0]},
         "result": [2, 0], "post": {"points": 1, "brier": 0.16, "info_bits": 0.001}},
        {"match": 7, "fixture": "Brazil v Morocco", "failure_mode": None,
         "pre": {"pick": [2, 0]},
         "result": [1, 1], "post": {"points": 0, "brier": 0.96, "info_bits": 0.001}},
        {"match": 8, "fixture": "Qatar v Switzerland", "failure_mode": None,
         "pre": {"pick": [0, 1]},
         "result": [1, 1], "post": {"points": 0, "brier": 1.22, "info_bits": 0.003}},
    ]
    tex = re_.ledger_table(ents, issue_order=[1, 8, 7])
    assert "G & M & Fixture" in tex                 # G column first, before M
    assert "Info (bits)" in tex                     # absorbed bits column
    assert "KL divergence contribution" in tex      # folded-in note
    # issue order: match 8 (G2) precedes match 7 (G3), not by schedule number
    assert tex.index("Qatar v Switzerland") < tex.index("Brazil v Morocco")


def test_ledger_table_empty_is_a_placeholder_not_broken_latex():
    tex = re_.ledger_table([])
    assert "longtable" not in tex
    assert "&" not in tex          # no bare alignment chars
    assert "No matches documented yet" in tex


def test_ledger_table_upcoming_rows_show_three_track_picks():
    upcoming = [
        {"match": 12, "fixture": "Japan v Tunisia",
         "frozen_pick": [2, 0], "track_a_pick": [2, 0], "track_b_pick": [2, 1]},
        {"match": 13, "fixture": "Sweden v Tunisia",
         "frozen_pick": [1, 1], "track_a_pick": [1, 1], "track_b_pick": [1, 0]},
    ]
    tex = re_.ledger_table(ENTRIES, upcoming=upcoming)
    assert "Upcoming fixtures" in tex
    assert "Japan v Tunisia" in tex
    # Track B diverges from Frozen/Track A on the upcoming rows
    assert "2--0 & 2--0 & 2--1" in tex
    assert "1--1 & 1--1 & 1--0" in tex
    # played entry still present with dashed track-pick columns
    assert "Mexico v South Africa" in tex


def test_ledger_table_upcoming_only_renders_without_played_entries():
    upcoming = [{"match": 1, "fixture": "A v B",
                 "frozen_pick": [1, 0], "track_a_pick": [1, 0], "track_b_pick": [2, 0]}]
    tex = re_.ledger_table([], upcoming=upcoming)
    assert "longtable" in tex and "A v B" in tex


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


def test_divergence_folds_in_drift_column():
    # The learning-track Elo drift table is absorbed into Table 6 as a final
    # column. A drifter absent from frozen/now is skipped (no KeyError).
    drift = {"South Korea": 75.0, "Czechia": -65.3, "Spain": 3.2,
             "NotARealTeam": 40.0}
    tex = re_.divergence_section(FROZEN, NOW, ENTRIES, GS, drift=drift)
    assert "Drift (Elo)" in tex            # new column header
    assert "$+75.0$" in tex                # South Korea drift
    assert "$-65.3$" in tex                # Czechia drift
    assert "$+3.2$" in tex                 # Spain drift
    assert "NotARealTeam" not in tex       # absent from frozen -> skipped safely


def test_divergence_track_b_deltas_are_b_minus_frozen():
    champion_b = {"Spain": 0.271, "Argentina": 0.177, "France": 0.141}
    now_b = {
        "Spain":       {"advance_KO": 0.950},
        "Argentina":   {"advance_KO": 0.989},
        "France":      {"advance_KO": 0.999},
    }
    tex = re_.divergence_section(FROZEN, NOW, ENTRIES, GS,
                                 champion_b=champion_b, now_b=now_b)
    # both Δ columns are labelled (B$-$F)
    assert tex.count("$\\Delta$ (B$-$F)") >= 2
    assert "A$-$Frozen" not in tex
    # Champion Δ Spain: 27.1 (B) − 26.9 (Frozen) = +0.2
    assert "$+0.2$" in tex
    # Advance Δ Spain: 95.0 (B) − 98.9 (Frozen) = −3.9
    assert "$-3.9$" in tex
    # Teams without Track B data (movers South Korea/Czechia) get --- deltas
    assert "---" in tex


def test_champ_table_ranks_by_now_and_keeps_frozen_column():
    tex = re_.champ_table(FROZEN, NOW, 2)
    assert "Champion (Frozen)" in tex and "Champion (Track~A)" in tex
    assert "label{tab:champ}" in tex
    assert tex.index("Spain") < tex.index("Argentina") < tex.index("France")
    assert "26.9\\%" in tex                               # frozen column value
    assert "conditioned on the 2 results" in tex
    assert tex.count("\\begin{table}") == tex.count("\\end{table}") == 1


def test_champ_table_has_b_uses_frozen_not_lock():
    b = {"Spain": 0.272, "Argentina": 0.177, "France": 0.141,
         "South Korea": 0.001, "Czechia": 0.000}
    tex = re_.champ_table(FROZEN, NOW, 2, champion_b=b)
    assert "Lock" not in tex
    assert "Frozen" in tex
    assert "Track~A" in tex
    assert "Track~B" in tex


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
    assert "Track~A" in tex
    assert "Track~B" in tex
    assert r"\Delta" in tex
    assert "27.1\\%" in tex   # Spain Track B
    # Δ column is now Track B − Frozen (B$-$F), not A−Frozen
    assert "$\\Delta$ (B$-$F)" in tex
    assert "Track~B champion probability minus Frozen" in tex
    # Spain: 27.1 (B) − 26.9 (Frozen) = +0.2
    assert "+0.2" in tex
    # France: 13.8 (B) − 14.3 (Frozen) = −0.5
    assert "-0.5" in tex
    # Teams absent from champion_b (South Korea, Czechia) get --- delta
    assert "---" in tex
    assert r"\label{tab:champ}" in tex
    assert tex.count(r"\begin{table}") == tex.count(r"\end{table}") == 1


def test_champ_table_folds_in_market_column():
    # The former market-snapshot table's Market column now lives in champ_table.
    market = {"Spain": 0.130, "Argentina": 0.111, "France": 0.180}
    tex = re_.champ_table(FROZEN, NOW, 2, champion_b=CHAMPION_B, market=market)
    assert "Market (\\%)" in tex                 # new column header
    assert "Market = live Polymarket" in tex     # note explains it
    assert "13.0\\%" in tex                       # Spain market
    assert "18.0\\%" in tex                       # France market
    # Teams with no market value render --- in that cell
    assert "---" in tex


def test_champ_table_market_optional():
    # Without market data the Market column degrades to --- (no crash).
    tex = re_.champ_table(FROZEN, NOW, 2, champion_b=CHAMPION_B)
    assert "Market (\\%)" in tex
    assert tex.count(r"\begin{table}") == 1

def test_champ_table_without_champion_b_renders_frozen_track_a():
    tex = re_.champ_table(FROZEN, NOW, 2)
    assert "Track~B" not in tex
    assert "Champion (Track~A)" in tex
    assert "Champion (Frozen)" in tex
    assert r"\label{tab:champ}" in tex
