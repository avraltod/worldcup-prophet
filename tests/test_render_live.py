"""render_live: each living unit renders to its own paper/live/*.tex file; the
skeleton is asserted byte-identical via its stored sha256."""
import hashlib

import render_live as rl
import draft_sections as ds


def _entry(m=1, pts=1, bits=0.001):
    return {"match": m, "fixture": "Mexico v South Africa", "result": [2, 0],
            "failure_mode": None, "interpretation": "text", "kickoff": "2026-06-11T19:00:00Z",
            "pre": {"pick": [2, 1], "probs_HDA": [0.67, 0.21, 0.12]},
            "post": {"points": pts, "brier": 0.166, "p_outcome": 0.67,
                     "info_bits": bits, "movers": []}}


def _stages(champ=0.269):
    base = {"advance_KO": 0.99, "R16": 0.8, "QF": 0.6, "SF": 0.5,
            "final": 0.39, "champion": champ}
    return {t: dict(base) for t in ("Spain", "Argentina", "France", "Portugal",
                                    "England", "Brazil", "Mexico", "Germany",
                                    "Netherlands", "Ecuador")}


def test_skeleton_hash_is_plain_sha256():
    assert rl.skeleton_hash("abc") == hashlib.sha256(b"abc").hexdigest()


def test_outcome_probs_normalized():
    ph, pd, pa = rl.outcome_probs(1.9, 0.65)
    assert abs(ph + pd + pa - 1.0) < 1e-12
    assert ph > pa                       # stronger attack wins more often


def test_write_unit_creates_file(tmp_path):
    rl.write_unit(tmp_path, "ledger", "CONTENT")
    f = tmp_path / "ledger.tex"
    assert f.exists()
    text = f.read_text()
    assert "GENERATED" in text and "CONTENT" in text


def test_ported_units_render(tmp_path):
    entries = [_entry()]
    frozen, now = _stages(), _stages(0.27)
    gs = [{"group": "A", "played": 1, "total": 6, "rows": [
        {"team": "Mexico", "P": 1, "W": 1, "D": 0, "L": 0, "GF": 2, "GA": 0, "Pts": 3},
        {"team": "South Africa", "P": 1, "W": 0, "D": 0, "L": 1, "GF": 0, "GA": 2, "Pts": 0}]}]
    out = {
        "ledger": rl.ledger(entries),
        "narrative": rl.narrative_unit(entries),
        "trajfig": rl.trajfig_unit(entries, live_fig=True),
        "champ_table": rl.champ_table_unit(frozen, now, 1),
        "divergence": rl.divergence_unit(frozen, now, entries, gs),
    }
    assert "longtable" in out["ledger"]
    assert "Mexico v South Africa" in out["ledger"]
    assert "fig_trajectory_live" in out["trajfig"]
    assert "tab:champ" in out["champ_table"]
    assert "Group A" in out["divergence"] and "Mexico 3 pts" in out["divergence"]


def _gs12(played_a=True):
    def rows(names, pts=None):
        return [{"team": n, "P": 1 if pts else 0, "W": 1 if pts and p == 3 else 0,
                 "D": 0, "L": 1 if pts and p == 0 else 0,
                 "GF": 2 if pts and p == 3 else 0, "GA": 2 if pts and p == 0 else 0,
                 "Pts": p or 0}
                for n, p in zip(names, pts or [None] * len(names))]
    gs = []
    for g in "ABCDEFGHIJKL":
        names = [f"{g}{i}" for i in range(1, 5)]
        if g == "A" and played_a:
            gs.append({"group": "A", "played": 1, "total": 6,
                       "rows": rows(["Mexico", "South Korea", "Czechia", "South Africa"],
                                    [3, 0, 0, 0])})
        else:
            gs.append({"group": g, "played": 0, "total": 6, "rows": rows(names)})
    return gs


def test_tracker_lists_all_twelve_groups():
    frozen, now = _stages(), _stages(0.27)
    for t in ("Mexico", "South Korea", "Czechia", "South Africa"):
        frozen[t] = now[t] = {"advance_KO": 0.5, "R16": 0.2, "QF": 0.1,
                              "SF": 0.05, "final": 0.02, "champion": 0.01}
    tex = rl.tracker(_gs12(), frozen, now)
    assert tex.count("\\\\") >= 12 and "Mexico" in tex


def test_group_box_played_and_unplayed():
    frozen, now = _stages(), _stages(0.27)
    for t in ("Mexico", "South Korea", "Czechia", "South Africa"):
        frozen[t] = {"advance_KO": 0.9, "champion": 0.01, "R16": 0, "QF": 0, "SF": 0, "final": 0}
        now[t] = {"advance_KO": 0.95, "champion": 0.01, "R16": 0, "QF": 0, "SF": 0, "final": 0}
    exps = [{"match": 1, "group": "A", "home": "Mexico", "away": "South Africa",
             "pick": [2, 1], "probs_HDA": [0.67, 0.21, 0.12]},
            {"match": 2, "group": "A", "home": "South Korea", "away": "Czechia",
             "pick": [1, 1], "probs_HDA": [0.35, 0.33, 0.32]}]
    gA = next(g for g in _gs12() if g["group"] == "A")
    tex = rl.group_box(gA, {"group": {"1": [2, 0]}}, exps, frozen, now)
    assert "2--0" in tex                      # real result in matrix cell
    assert "F/A/B:1--1" in tex                # upcoming scoreline (no track_b: all agree)
    assert "H/D/A" not in tex                 # H/D/A no longer in the group box
    gB = next(g for g in _gs12() if g["group"] == "B")
    tex_b = rl.group_box(gB, {"group": {}}, [], frozen, now)
    assert "Fixtures pending" in tex_b      # no expectations supplied


def test_group_box_panels_and_track_scorelines():
    frozen, now = _stages(), _stages(0.27)
    for t in ("Mexico", "South Korea", "Czechia", "South Africa"):
        frozen[t] = {"advance_KO": 0.9, "champion": 0.01, "R16": 0, "QF": 0, "SF": 0, "final": 0}
        now[t] = {"advance_KO": 0.95, "champion": 0.01, "R16": 0, "QF": 0, "SF": 0, "final": 0}
    exps = [{"match": 1, "group": "A", "home": "Mexico", "away": "South Africa",
             "pick": [2, 1], "probs_HDA": [0.67, 0.21, 0.12]},
            {"match": 2, "group": "A", "home": "South Korea", "away": "Czechia",
             "pick": [1, 1], "probs_HDA": [0.35, 0.33, 0.32]}]
    # Track B predicts a different scoreline for the unplayed match 2
    track_b = {2: {"pick": [2, 0], "hda": [0.55, 0.25, 0.20]}}
    gA = next(g for g in _gs12() if g["group"] == "A")
    tex = rl.group_box(gA, {"group": {"1": [2, 0]}}, exps, frozen, now, track_b=track_b)
    # four panel headers: Actual (no Q%), Frozen/Track A/Track B (with Q%)
    assert "\\makecell{Actual \\\\ W/D/L/P}" in tex     # Actual drops Q%
    assert "\\makecell{Frozen \\\\ W/D/L/P/Q\\%}" in tex
    assert "Track~A" in tex and "Track~B" in tex
    assert "worldflag" in tex                  # flag column headers, not country names
    # full-width table + 3-letter team codes
    assert "tabular*" in tex and "\\textwidth" in tex
    assert "MEX" in tex and "KOR" in tex       # ISO3 codes, not full names
    # upcoming cell: scoreline only, Frozen=Track A merged, Track B if it differs
    assert "F/A:1--1\\, B:2--0" in tex         # match 2: F/A 1-1, Track B 2-0
    # no H/D/A and no separate fixtures table in the group box
    assert "H/D/A" not in tex
    assert "Fixture &" not in tex


def test_group_box_shows_pred_vs_actual_in_matrix():
    frozen, now = _stages(), _stages(0.27)
    for t in ("Mexico", "South Korea", "Czechia", "South Africa"):
        frozen[t] = {"advance_KO": 0.9, "champion": 0.01, "R16": 0, "QF": 0, "SF": 0, "final": 0}
        now[t] = {"advance_KO": 0.95, "champion": 0.01, "R16": 0, "QF": 0, "SF": 0, "final": 0}
    exps = [{"match": 1, "group": "A", "home": "Mexico", "away": "South Africa",
              "pick": [2, 1], "probs_HDA": [0.67, 0.21, 0.12]},
             {"match": 2, "group": "A", "home": "South Korea", "away": "Czechia",
              "pick": [1, 1], "probs_HDA": [0.35, 0.33, 0.32]}]
    gA = next(g for g in _gs12() if g["group"] == "A")
    tex = rl.group_box(gA, {"group": {"1": [2, 0]}}, exps, frozen, now)
    assert "2--0" in tex                         # played result in matrix cell
    assert "checkmark" in tex                    # pick 2-1 (home win) vs actual 2-0 (home win) ✓
    assert "Q\\%" in tex and "95.0" in tex       # Actual panel folds Track A qual% (now)
    assert "tabular" in tex                      # unified table structure


def _learning():
    return {"drift": {"Mexico": 6.2, "South Africa": -6.2},
            "pending": [],
            "processed": [{"match": 1, "home": "Mexico", "away": "South Africa",
                           "lam_obs": {"home": 1.9, "away": 0.4, "source": "proxy"},
                           "lam_exp": {"home": 1.5, "away": 0.7},
                           "drift_after": {"Mexico": 6.2, "South Africa": -6.2}}]}


def test_two_track_unit():
    # The redundant champion table is gone: the unit is the A-vs-B narrative
    # plus the two-track figure, pointing to Table 3 (champions) and Table 6
    # (Elo drift).
    two = {"frozen": {"Spain": 0.27, "Argentina": 0.18},
           "learning": {"Spain": 0.28, "Argentina": 0.17}}
    tex = rl.two_track_unit(two, _learning(), fig=False)
    assert r"\label{sec:twotracklive}" in tex
    assert r"Table~\ref{tab:champ}" in tex          # champions live in Table 3
    assert r"Table~\ref{tab:live_divergence}" in tex  # drift folded into Table 6
    # no embedded champion/drift tabular here anymore
    assert "tabular" not in tex
    tex_fig = rl.two_track_unit(two, _learning(), fig=True)
    assert "fig_two_track_live" in tex_fig          # Figure 12 kept


def test_two_track_unit_no_embedded_tables():
    two = {"frozen": {"Spain": 0.27}, "learning": {"Spain": 0.28}}
    track_a = {"Spain": {"champion": 0.272}}
    tex = rl.two_track_unit(two, _learning(), fig=False, track_a=track_a,
                            champion_b={"Spain": 0.245})
    assert "tabular" not in tex            # champion table dropped (subset of Table 3)
    assert "Drift (Elo)" not in tex        # drift table dropped (folded into Table 6)


def test_revision_report_unit():
    ctx = {"match": 3, "entries": [_entry(1), _entry(3, pts=3, bits=0.02)],
           "match_stats": {3: {"home": {"team": "Canada", "sot": 5, "other_shots": 6,
                                        "total_shots": 11, "possession": 58.0},
                               "away": {"team": "Bosnia and Herzegovina", "sot": 2,
                                        "other_shots": 2, "total_shots": 4,
                                        "possession": 42.0}}},
           "learning": _learning(),
           "prev_now": _stages(0.27), "now": _stages(0.28),
           "vintages_rows": [
               {"edition": 0, "match": None, "fixture": None, "result": None,
                "points": None, "cum_points": 0, "mean_brier": None,
                "cum_bits": 0.0, "champ_top5": [["Spain", 0.269]]},
               {"edition": 3, "match": 3, "fixture": "Canada v Bosnia and Herzegovina",
                "result": [2, 0], "points": 3, "cum_points": 4, "mean_brier": 0.2,
                "cum_bits": 0.02, "champ_top5": [["Spain", 0.28]]}],
           "revision_narrative": "The forecast moved because of the result.",
           "implications": [{"match": 5, "fixture": "Canada v Qatar",
                             "lock_HDA": [0.5, 0.3, 0.2], "learn_HDA": [0.55, 0.27, 0.18]}]}
    tex = rl.revision_report(ctx)
    assert "Revision report: edition M003" in tex
    assert "M000" in tex                       # vintages table embedded
    assert "Canada v Qatar" in tex             # implications
    # revision_narrative dropped per spec §3.10 (duplicated forecast revision para)


def test_validate_labels_passes_when_present():
    rl.validate_labels("test", r"\label{tab:live_foo} content", ["tab:live_foo"])


def test_validate_labels_raises_when_missing():
    import pytest
    with pytest.raises(ValueError, match="tab:live_bar"):
        rl.validate_labels("test", "content without label", ["tab:live_bar"])


def test_validate_labels_empty_requirements_always_passes():
    rl.validate_labels("test", "any content", [])


def test_ledger_has_label():
    entries = [_entry()]
    tex = rl.ledger(entries)
    assert r"\label{tab:live_ledger}" in tex


def test_divergence_has_label():
    frozen, now = _stages(), _stages(0.27)
    gs = [{"group": "A", "played": 1, "total": 6,
           "rows": [{"team": "Mexico", "P": 1, "W": 1, "D": 0, "L": 0,
                     "GF": 2, "GA": 0, "Pts": 3}]}]
    tex = rl.divergence_unit(frozen, now, [_entry()], gs)
    assert r"\label{tab:live_divergence}" in tex


def _ctx_for_report():
    return {"match": 3, "entries": [_entry(1), _entry(3, pts=3, bits=0.02)],
            "match_stats": {3: {"home": {"team": "Canada", "sot": 5, "other_shots": 6,
                                         "total_shots": 11, "possession": 58.0},
                                "away": {"team": "BIH", "sot": 2,
                                         "other_shots": 2, "total_shots": 4,
                                         "possession": 42.0}}},
            "learning": _learning(),
            "prev_now": _stages(0.27), "now": _stages(0.28),
            "vintages_rows": [
                {"edition": 0, "match": None, "fixture": None, "result": None,
                 "points": None, "cum_points": 0, "mean_brier": None,
                 "cum_bits": 0.0, "champ_top5": [["Spain", 0.269]]},
                {"edition": 3, "match": 3, "fixture": "Canada v BIH", "result": [1, 1],
                 "points": 0, "cum_points": 1, "mean_brier": 0.45,
                 "cum_bits": 0.02, "champ_top5": [["Spain", 0.28]]}],
            "revision_narrative": "Test narrative.",
            "implications": []}

def test_revision_report_match_stats_table_has_label():
    # Table 7: cumulative match stats — label changed per spec §3.10
    ctx = _ctx_for_report()
    ctx["expectations"] = [{"match": 3, "probs_HDA": [0.5, 0.25, 0.25]}]
    tex = rl.revision_report(ctx)
    assert r"\label{tab:live_match_stats}" in tex


def test_cumulative_stats_table_shows_track_b_column_when_probs_hda_b_present():
    # Track B column appears when at least one entry has pre.probs_HDA_b stored
    entries = [{"match": 3, "fixture": "Canada v BIH",
                "pre": {"probs_HDA": [0.5, 0.25, 0.25],
                        "probs_HDA_b": [0.55, 0.23, 0.22]}}]
    match_stats = {3: {"home": {"team": "Canada", "total_shots": 11, "sot": 5,
                                "possession": 58.0},
                       "away": {"team": "BIH", "total_shots": 4, "sot": 2,
                                "possession": 42.0}}}
    tex = rl._cumulative_stats_table(entries, match_stats,
                                     [{"match": 3, "probs_HDA": [0.5, 0.25, 0.25]}])
    assert "Track~B" in tex
    assert "55.0" in tex    # Track B home prob


def test_cumulative_stats_table_orders_by_issue_order_and_pads():
    # Issue order [1, 8, 7]: match 8 (G02) precedes match 7 (G03) even though
    # 7 < 8 by schedule number. Shots/on-target are zero-padded 2-digit integers.
    entries = [
        {"match": 1, "fixture": "Mexico v South Africa",
         "pre": {"probs_HDA": [0.6, 0.2, 0.2]}},
        {"match": 7, "fixture": "Brazil v Morocco",
         "pre": {"probs_HDA": [0.6, 0.2, 0.2]}},
        {"match": 8, "fixture": "Qatar v Switzerland",
         "pre": {"probs_HDA": [0.6, 0.2, 0.2]}},
    ]
    match_stats = {
        1: {"home": {"total_shots": 16.0, "sot": 4.0, "possession": 60.0},
            "away": {"total_shots": 3.0, "sot": 2.0, "possession": 40.0}},
        7: {"home": {"total_shots": 13.0, "sot": 5.0, "possession": 51.0},
            "away": {"total_shots": 14.0, "sot": 3.0, "possession": 49.0}},
        8: {"home": {"total_shots": 7.0, "sot": 4.0, "possession": 32.0},
            "away": {"total_shots": 26.0, "sot": 7.0, "possession": 68.0}},
    }
    exps = [{"match": m, "probs_HDA": [0.6, 0.2, 0.2]} for m in (1, 7, 8)]
    tex = rl._cumulative_stats_table(entries, match_stats, exps,
                                     issue_order=[1, 8, 7])
    # G02 is match 8, G03 is match 7 (issue order, not schedule order)
    assert "G02 M08 Qatar v Switzerland" in tex
    assert "G03 M07 Brazil v Morocco" in tex
    assert tex.index("G02 M08") < tex.index("G03 M07")
    # zero-padded 2-digit integer shots/on-target (7 -> 07, 16 -> 16)
    assert "07--26" in tex        # match 8 shots
    assert "16--03" in tex        # match 1 shots
    assert "04--02" in tex        # match 1 on target


def test_cumulative_stats_table_no_track_b_column_when_missing():
    entries = [{"match": 3, "fixture": "Canada v BIH",
                "pre": {"probs_HDA": [0.5, 0.25, 0.25]}}]
    match_stats = {3: {"home": {"team": "Canada", "total_shots": 11, "sot": 5,
                                "possession": None},
                       "away": {"team": "BIH", "total_shots": 4, "sot": 2,
                                "possession": None}}}
    tex = rl._cumulative_stats_table(entries, match_stats, [])
    assert "Track~B" not in tex
    assert r"\label{tab:live_match_stats}" in tex


def test_revision_report_vintages_table_has_label():
    tex = rl.revision_report(_ctx_for_report())
    assert r"\label{tab:live_vintages}" in tex


def _full_ctx():
    """Shared context object for testing new units."""
    entries = [_entry(1, pts=1, bits=0.001), _entry(4, pts=1, bits=0.002)]
    for e in entries:
        e["post"]["p_outcome"] = 0.43 if e["match"] == 4 else 0.67
    return {
        "match": 4, "n_results": 4, "cum_points": 2, "mean_brier": 0.52,
        "champ_now_top": [("Spain", 0.270), ("Argentina", 0.180), ("France", 0.142)],
        "entries": entries,
        "champion_movers": [["Spain", 0.269, 0.270], ["South Korea", 0.08, 0.20]],
        "two_track": {"frozen": {"Spain": 0.270}, "learning": {"Spain": 0.268}},
        "learning": {"drift": {"United States": 75.0, "Paraguay": -75.0},
                     "processed": [{"match": 4,
                                    "lam_obs": {"home": 1.95, "away": 0.33},
                                    "lam_exp": {"home": 0.90, "away": 1.50}}]},
        "frozen": {"Spain": {"advance_KO": 0.99, "champion": 0.269},
                   "South Korea": {"advance_KO": 0.50, "champion": 0.08},
                   "Argentina": {"advance_KO": 0.98, "champion": 0.179}},
        "now": {"Spain": {"advance_KO": 0.99, "champion": 0.270},
                "South Korea": {"advance_KO": 0.77, "champion": 0.20},
                "Argentina": {"advance_KO": 0.98, "champion": 0.180}},
        "expectations": [],
        "group_state": [],
        "results": {"group": {"1": [2, 0], "4": [4, 1]}, "ko": {}},
    }

def test_abstract_live_unit():
    tex = rl.abstract_live_unit(_full_ctx())
    assert "Spain" in tex and "27.0" in tex

def test_intro_data_note_unit():
    tex = rl.intro_data_note_unit(_full_ctx())
    assert "Track~A" in tex and "Track~B" in tex

def test_simulation_note_unit():
    tex = rl.simulation_note_unit(_full_ctx())
    assert "100" in tex  # 104-4 remaining

def test_data_revealed_unit():
    tex = rl.data_revealed_unit(_full_ctx())
    # table folded into the ledger; section points there now
    assert r"tab:live_data_revealed" not in tex
    assert r"Table~\ref{tab:live_ledger}" in tex

def test_sec36_live_unit():
    tex = rl.sec36_live_unit(_full_ctx())
    assert "bits" in tex.lower()

def test_robustness_live_unit():
    tex = rl.robustness_live_unit(_full_ctx())
    assert r"\label{sec:live_robust}" in tex

def test_failure_analysis_unit_no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    tex = rl.failure_analysis_unit(_full_ctx())
    assert r"\label{sec:live_failure}" in tex

def test_discussion_live_unit():
    tex = rl.discussion_live_unit(_full_ctx())
    assert len(tex) > 20

def test_groupqual_live_unit():
    tex = rl.groupqual_live_unit(_full_ctx())
    assert r"\label{fig:live_groupqual}" in tex
    assert r"\label{fig:live_groupqual_b}" in tex
    # discussion paragraph referencing the locked Frozen figure
    assert "Qualification, three ways" in tex
    assert r"Figure~\ref{fig:groupqual}" in tex

def test_bracket_live_unit_group_stage_shows_slot_risk_table():
    ctx = _full_ctx()
    ctx["results"] = {"group": {}, "ko": {}}
    tex = rl.bracket_live_unit(ctx)
    assert r"\label{tab:live_slot_risk}" in tex
    assert "R32 slot risk" in tex
    assert "KO Pick" in tex
    assert "Frozen" in tex
    # the three-bracket discussion + live Track A/B bracket figures are now always shown
    assert "bracket, three ways" in tex
    assert "fig_live_bracket_a.pdf" in tex and "fig_live_bracket_b.pdf" in tex
    assert r"Figure~\ref{fig:bracket}" in tex   # references the locked Frozen bracket


def test_bracket_live_unit_group_stage_with_track_b():
    ctx = _full_ctx()
    ctx["results"] = {"group": {}, "ko": {}}
    ctx["now_b"] = {"Spain": {"advance_KO": 0.99, "champion": 0.25}}
    tex = rl.bracket_live_unit(ctx)
    assert "Track~B" in tex
    assert r"\checkmark" in tex or r"\triangle" in tex or r"\times" in tex

def test_survival_colcomp_unit():
    ctx = _full_ctx()
    tex = rl.survival_colcomp_unit(ctx)
    assert r"\label{tab:live_survcomp}" in tex
    assert "Spain" in tex
    assert "/" in tex  # frozen/now pair format


def test_two_track_unit_provenance_moved_to_data_revealed():
    # Track B provenance block lives in data_revealed now, not two_track
    two_track = {"frozen": {"Spain": 0.142, "Argentina": 0.213},
                 "learning": {"Spain": 0.158, "Argentina": 0.201}}
    learning = {"drift": {"Mexico": -49.94}, "processed": [{"match": 1}],
                "pending": []}
    info = {
        "fetched_at": "2026-06-13T12:47:00Z",
        "elo_rms_delta": 15.2,
        "n_rate_changes": 14,
    }
    out = rl.two_track_unit(two_track, learning, fig=False, info_snapshot=info)
    assert "2026-06-13" not in out      # date state NOT in two_track anymore
    assert "15.2" not in out            # rms delta NOT in two_track anymore
    assert "Track~B" in out             # section still renders with correct label
    # drift now lives in the divergence table (Table 6), referenced here
    assert r"Table~\ref{tab:live_divergence}" in out


def test_two_track_unit_no_provenance_when_snapshot_absent():
    two_track = {"frozen": {"Spain": 0.142}, "learning": {"Spain": 0.158}}
    learning = {"drift": {}, "processed": [], "pending": []}
    out = rl.two_track_unit(two_track, learning, fig=False, info_snapshot=None)
    assert "Track" in out               # still renders the narrative


def test_market_snap_unit_no_market():
    ctx = {"now": {"Spain": {"champion": 0.27}, "France": {"champion": 0.14}},
           "frozen": {"Spain": {"champion": 0.269}, "France": {"champion": 0.143}},
           "champion_b": {}, "market": None}
    out = rl.market_snap_unit(ctx)
    assert "not yet available" in out
    # The consolidated figure (and its label) is emitted even without market data
    # so the baseline references to Figure~\ref{fig:live_market} always resolve.
    assert r"\label{fig:live_market}" in out
    # The snapshot table is folded into the headline champ table; not here anymore.
    assert "tab:live_market_snap" not in out


def test_market_snap_unit_with_market():
    ctx = {"now": {"Spain": {"champion": 0.27}, "France": {"champion": 0.14}},
           "frozen": {"Spain": {"champion": 0.269}, "France": {"champion": 0.143}},
           "champion_b": {"Spain": 0.275, "France": 0.135},
           "market": {"Spain": 0.30, "France": 0.12}}
    out = rl.market_snap_unit(ctx)
    # Table removed; the consolidated figure + the model-vs-market status remain.
    assert r"\label{fig:live_market}" in out
    assert "tab:live_market_snap" not in out
    assert "Market" in out          # described in the figure note
    assert "broadly agree" in out   # market-present status line


# ---- Table 10: three-panel finishing-position table ----

def _group_state_AB():
    return [
        {"group": "A", "played": 2, "total": 6,
         "rows": [{"team": "Mexico", "Pts": 3}, {"team": "South Korea", "Pts": 3},
                  {"team": "Czechia", "Pts": 0}, {"team": "South Africa", "Pts": 0}]},
        {"group": "B", "played": 2, "total": 6,
         "rows": [{"team": "Switzerland", "Pts": 1}, {"team": "Canada", "Pts": 1},
                  {"team": "Bosnia and Herzegovina", "Pts": 1}, {"team": "Qatar", "Pts": 1}]},
    ]


def _finish(first, second, third, qual):
    return {"first": first, "second": second, "third_adv": third,
            "advance_KO": qual, "champion": 0.1}


def test_groupqual_table_three_panel_14_cols():
    ctx = {
        "frozen_finish": {
            "A": {"Mexico": {"p1": 0.55, "p2": 0.26, "p3adv": 0.11, "qual": 0.91},
                  "South Korea": {"p1": 0.18, "p2": 0.28, "p3adv": 0.21, "qual": 0.66},
                  "Czechia": {"p1": 0.19, "p2": 0.29, "p3adv": 0.20, "qual": 0.68},
                  "South Africa": {"p1": 0.08, "p2": 0.18, "p3adv": 0.19, "qual": 0.45}}},
        "now": {"Mexico": _finish(0.68, 0.23, 0.08, 0.99),
                "South Korea": _finish(0.26, 0.47, 0.19, 0.92)},
        "now_b": {"Mexico": _finish(0.52, 0.34, 0.13, 0.99)},
        "group_state": _group_state_AB(),
    }
    out = rl.groupqual_table_unit(ctx)
    # three panel headers
    assert out.count(r"\multicolumn{4}{c}") == 3
    assert r"\multicolumn{4}{c}{Frozen}" in out
    assert r"\multicolumn{4}{c}{Track~A}" in out
    assert r"\multicolumn{4}{c}{Track~B}" in out
    # 14-column tabular: ll + 12 numeric
    assert r"\begin{tabular}{llrrrrrrrrrrrr}" in out
    assert r"\cmidrule(lr){3-6}\cmidrule(lr){7-10}\cmidrule(lr){11-14}" in out
    # Frozen panel matches locked Table 13 (Mexico 55/26/11/91)
    assert "Mexico & 55 & 26 & 11 & \\textbf{91}" in out
    # Track A populated (Mexico 68/23/8/99); Track B (52/34/13/99)
    assert "68 & 23 & 8 & \\textbf{99}" in out
    assert "52 & 34 & 13 & \\textbf{99}" in out
    # team lacking Track B shows dashes in its B panel
    assert "--" in out
    assert r"\label{tab:live_groupqual_three}" in out


def test_groupqual_table_abbreviates_long_names():
    ctx = {
        "frozen_finish": {"B": {"Bosnia and Herzegovina":
                                {"p1": 0.1, "p2": 0.24, "p3adv": 0.28, "qual": 0.62}}},
        "now": {}, "now_b": {},
        "group_state": [{"group": "B", "played": 0, "total": 6,
                         "rows": [{"team": "Bosnia and Herzegovina", "Pts": 0}]}],
    }
    out = rl.groupqual_table_unit(ctx)
    assert "Bosnia and He." in out           # matches locked Table 13 style
    assert "Bosnia and Herzegovina &" not in out


def test_groupqual_table_no_group_state():
    out = rl.groupqual_table_unit({"frozen_finish": {}, "group_state": []})
    assert "not yet available" in out


# ---- Table 11: pre-registered risk tracker ----

def _frozen_finish_full():
    # minimal: submitted top-2 per group A and D
    return {
        "A": {"Mexico": {"p1": 0.55, "p2": 0.26}, "Czechia": {"p1": 0.19, "p2": 0.29},
              "South Korea": {"p1": 0.18, "p2": 0.28}, "South Africa": {"p1": 0.08, "p2": 0.18}},
        "D": {"United States": {"p1": 0.37, "p2": 0.29}, "Turkey": {"p1": 0.35, "p2": 0.29},
              "Paraguay": {"p1": 0.18, "p2": 0.25}, "Australia": {"p1": 0.10, "p2": 0.17}},
    }


def test_risk_tracker_all_twelve_groups_and_labels():
    ctx = {"frozen_finish": _frozen_finish_full(), "now": {},
           "group_state": [{"group": g, "played": 0, "total": 6,
                            "rows": [{"team": "X", "Pts": 0}]} for g in "ABCDEFGHIJKL"]}
    out = rl.risk_tracker_unit(ctx)
    assert r"\label{tab:live_risk_tracker}" in out
    # every group letter heads a row
    for g in "ABCDEFGHIJKL":
        assert f"  {g} & " in out
    # pre-registered risk text carried verbatim
    assert "Czechia (68\\% qual.) takes second ahead of South Korea" in out


def test_risk_tracker_reversed_when_complete_and_displaced():
    # Group A complete; actual top-2 = Czechia, Mexico (South Korea/frozen-2 dropped)
    ff = _frozen_finish_full()
    # frozen top-2 for A: Mexico (p1 max), then Czechia (p2 max) -> {Mexico, Czechia}
    ctx = {"frozen_finish": ff, "now": {},
           "group_state": [{"group": "A", "played": 6, "total": 6,
                            "rows": [{"team": "Mexico", "Pts": 12},
                                     {"team": "South Korea", "Pts": 9},
                                     {"team": "Czechia", "Pts": 4},
                                     {"team": "South Africa", "Pts": 1}]}]}
    out = rl.risk_tracker_unit(ctx)
    # current top-2 = {Mexico, South Korea}; frozen = {Mexico, Czechia} -> reversed
    assert r"$\times$ Reversed" in out


def test_risk_tracker_resolved_when_complete_and_held():
    ff = _frozen_finish_full()
    ctx = {"frozen_finish": ff, "now": {},
           "group_state": [{"group": "A", "played": 6, "total": 6,
                            "rows": [{"team": "Mexico", "Pts": 12},
                                     {"team": "Czechia", "Pts": 9},
                                     {"team": "South Korea", "Pts": 4},
                                     {"team": "South Africa", "Pts": 1}]}]}
    out = rl.risk_tracker_unit(ctx)
    assert r"\checkmark\ Resolved" in out


def test_risk_tracker_no_frozen_finish():
    out = rl.risk_tracker_unit({"frozen_finish": {}, "now": {}, "group_state": []})
    assert "unavailable" in out
