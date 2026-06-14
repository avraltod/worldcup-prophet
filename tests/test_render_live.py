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
    assert "35.0" in tex                      # remaining fixture H% in matrix cell
    gB = next(g for g in _gs12() if g["group"] == "B")
    tex_b = rl.group_box(gB, {"group": {}}, [], frozen, now)
    assert "No results yet" in tex_b


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
    assert "Q" in tex and "90.0" in tex          # frozen qual% column present
    assert "tabular" in tex                      # unified table structure


def test_survival_unit_restates_all_teams():
    frozen, now = _stages(), _stages(0.30)
    tex = rl.survival_unit(frozen, now)
    assert "Spain" in tex and "30.0" in tex and "longtable" in tex


def _learning():
    return {"drift": {"Mexico": 6.2, "South Africa": -6.2},
            "pending": [],
            "processed": [{"match": 1, "home": "Mexico", "away": "South Africa",
                           "lam_obs": {"home": 1.9, "away": 0.4, "source": "proxy"},
                           "lam_exp": {"home": 1.5, "away": 0.7},
                           "drift_after": {"Mexico": 6.2, "South Africa": -6.2}}]}


def test_two_track_unit():
    two = {"frozen": {"Spain": 0.27, "Argentina": 0.18},
           "learning": {"Spain": 0.28, "Argentina": 0.17}}
    tex = rl.two_track_unit(two, _learning(), fig=False)
    assert "Spain" in tex and "27.0" in tex and "28.0" in tex
    # 3-col without track_a: Frozen | Track~B | Δ
    assert "Spain & 27.0 & 28.0 & +1.0" in tex
    assert "Mexico" in tex                    # drift table
    tex_fig = rl.two_track_unit(two, _learning(), fig=True)
    assert "fig_two_track_live" in tex_fig


def test_two_track_unit_with_track_a_four_cols():
    two = {"frozen": {"Spain": 0.27, "Argentina": 0.18},
           "learning": {"Spain": 0.28, "Argentina": 0.17}}
    track_a = {"Spain": {"champion": 0.272}, "Argentina": {"champion": 0.179}}
    tex = rl.two_track_unit(two, _learning(), fig=False, track_a=track_a)
    # 4-col: Frozen | Track A | Track B | Δ(A-Frozen)
    assert "Track~A" in tex and "Track~B" in tex
    assert "27.2" in tex   # Track A Spain
    assert "28.0" in tex   # Track B Spain (learning)
    # Δ = Track A - Frozen = 27.2 - 27.0 = +0.2
    assert "+0.2" in tex


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


def test_survival_unit_has_label():
    frozen, now = _stages(), _stages(0.30)
    tex = rl.survival_unit(frozen, now)
    assert r"\label{tab:live_survival}" in tex


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
    assert r"\label{tab:live_data_revealed}" in tex

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

def test_champdist_live_unit():
    tex = rl.champdist_live_unit(_full_ctx())
    assert r"\label{fig:live_champdist}" in tex

def test_groupqual_live_unit():
    tex = rl.groupqual_live_unit(_full_ctx())
    assert r"\label{fig:live_groupqual}" in tex

def test_bracket_live_unit_group_stage_shows_slot_risk_table():
    ctx = _full_ctx()
    ctx["results"] = {"group": {}, "ko": {}}
    tex = rl.bracket_live_unit(ctx)
    assert r"\label{tab:live_slot_risk}" in tex
    assert "R32 slot risk" in tex
    assert "KO Pick" in tex
    assert "Frozen" in tex


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
    assert "Drift" in out               # drift table still present


def test_two_track_unit_no_provenance_when_snapshot_absent():
    two_track = {"frozen": {"Spain": 0.142}, "learning": {"Spain": 0.158}}
    learning = {"drift": {}, "processed": [], "pending": []}
    out = rl.two_track_unit(two_track, learning, fig=False, info_snapshot=None)
    assert "frozen" in out.lower() or "Track" in out   # still renders the table


def test_market_snap_unit_no_market():
    ctx = {"now": {"Spain": {"champion": 0.27}, "France": {"champion": 0.14}},
           "frozen": {"Spain": {"champion": 0.269}, "France": {"champion": 0.143}},
           "champion_b": {}, "market": None}
    out = rl.market_snap_unit(ctx)
    assert r"\label{tab:live_market_snap}" in out
    assert "Spain" in out and "not yet available" in out


def test_market_snap_unit_with_market():
    ctx = {"now": {"Spain": {"champion": 0.27}, "France": {"champion": 0.14}},
           "frozen": {"Spain": {"champion": 0.269}, "France": {"champion": 0.143}},
           "champion_b": {"Spain": 0.275, "France": 0.135},
           "market": {"Spain": 0.30, "France": 0.12}}
    out = rl.market_snap_unit(ctx)
    assert r"\label{tab:live_market_snap}" in out
    assert "27.5" in out    # Track B Spain
    assert "30.0" in out    # Market Spain
    assert "Track~B" in out and "Market" in out
