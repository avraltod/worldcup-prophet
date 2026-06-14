import draft_sections as ds


def _ctx():
    return {
        "n_results": 4,
        "cum_points": 2,
        "mean_brier": 0.52,
        "champ_now_top": [("Spain", 0.270), ("Argentina", 0.180), ("France", 0.142)],
        "entries": [
            {"match": 1, "fixture": "Mexico v South Africa", "result": [2, 0],
             "post": {"points": 1, "brier": 0.166, "info_bits": 0.001,
                      "p_outcome": 0.67}, "pre": {"probs_HDA": [0.67, 0.21, 0.12]}},
            {"match": 4, "fixture": "United States v Paraguay", "result": [4, 1],
             "post": {"points": 1, "brier": 0.418, "info_bits": 0.002,
                      "p_outcome": 0.43}, "pre": {"probs_HDA": [0.43, 0.26, 0.31]}},
        ],
        "champion_movers": [
            ["Spain", 0.269, 0.270],
            ["South Korea", 0.08, 0.20],
            ["Paraguay", 0.05, 0.01],
        ],
        "two_track": {
            "frozen": {"Spain": 0.270, "Argentina": 0.179},
            "learning": {"Spain": 0.268, "Argentina": 0.181},
        },
        "learning": {"drift": {"United States": 75.0, "Paraguay": -75.0}, "processed": [
            {"match": 4, "lam_obs": {"home": 1.95, "away": 0.33},
             "lam_exp": {"home": 0.90, "away": 1.50}}
        ]},
        "frozen": {"Spain": {"advance_KO": 0.99, "champion": 0.269},
                   "South Korea": {"advance_KO": 0.50, "champion": 0.08}},
        "now": {"Spain": {"advance_KO": 0.99, "champion": 0.270},
                "South Korea": {"advance_KO": 0.77, "champion": 0.20}},
        "expectations": [
            {"match": 4, "group": "D", "home": "United States", "away": "Paraguay",
             "pick": [1, 0], "probs_HDA": [0.43, 0.26, 0.31]}
        ],
    }


def test_templated_abstract_live_contains_spain():
    text = ds.templated_abstract_live(_ctx())
    assert "Spain" in text and "27.0" in text


def test_templated_abstract_live_contains_brier():
    text = ds.templated_abstract_live(_ctx())
    assert "0.52" in text


def test_templated_intro_data_note_contains_n():
    text = ds.templated_intro_data_note(_ctx())
    assert "4" in text and "learning track" in text.lower()


def test_templated_simulation_note_contains_remaining():
    text = ds.templated_simulation_note(_ctx())
    assert "100 matches" in text  # 104 - 4 remaining


def test_templated_data_revealed_is_valid_latex():
    text = ds.templated_data_revealed(_ctx())
    assert r"\label{tab:live_data_revealed}" in text
    assert "Mexico v South Africa" in text


def test_templated_sec36_live_mentions_bits():
    text = ds.templated_sec36_live(_ctx())
    assert "bits" in text.lower() and "South Korea" in text


def test_templated_robustness_live_covers_all_four_decisions():
    text = ds.templated_robustness_live(_ctx())
    # Four bracket revision decisions are hard-coded from the paper
    assert "Norway" in text   # M78 Ecuador->Norway
    assert "Croatia" in text  # M83 Portugal->Croatia
    assert "Belgium" in text  # M94 United States->Belgium


def test_templated_failure_analysis_flags_high_brier():
    ctx = _ctx()
    # US 4-1 Paraguay: boost brier to exceed threshold
    ctx["entries"][1]["post"]["brier"] = 0.52
    text = ds.templated_failure_analysis(ctx)
    assert "United States" in text or "Paraguay" in text


def test_templated_failure_analysis_no_fabrication_when_all_ok():
    ctx = _ctx()
    # Set all p_outcome high and Brier low -> no failures
    for e in ctx["entries"]:
        e["post"]["p_outcome"] = 0.70
        e["post"]["brier"] = 0.20
    text = ds.templated_failure_analysis(ctx)
    assert "No material failures" in text


def test_templated_discussion_live_mentions_spain():
    text = ds.templated_discussion_live(_ctx())
    assert "Spain" in text


def test_draft_abstract_live_falls_back_to_template_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text, source = ds.draft_abstract_live(_ctx(), use_api=True)
    assert source == "template"
    assert "Spain" in text


def test_templated_simulation_note_v2_with_info_snapshot():
    ctx = _ctx()
    ctx["info_snapshot"] = {
        "elo_updated_at": "2026-06-13T19:00:00Z",
        "elo_rms_delta": 12.3,
        "n_rate_changes": 5,
        "max_odds_shift_ph": 0.04,
        "n_lineup_adj": 2,
        "n_teams_with_drift": 8,
    }
    text = ds.templated_simulation_note(ctx)
    assert "Track" in text and "B" in text
    assert "ClubElo" in text
    assert "2026-06-13" in text          # date portion of elo_updated_at
    assert "12.3" in text                # elo_rms_delta
    assert "5" in text                   # n_rate_changes
    assert "0.04" in text                # max_odds_shift_ph
    assert "2" in text                   # n_lineup_adj
    assert "8" in text                   # n_teams_with_drift
    assert "100 matches" in text          # 104 - 4 remaining, Para 1 still present


def test_templated_simulation_note_v1_fallback_no_key():
    ctx = _ctx()
    # no info_snapshot key → v1 one-sentence output only
    text = ds.templated_simulation_note(ctx)
    assert "ClubElo" not in text
    assert "100 matches" in text


def test_templated_simulation_note_v1_fallback_empty_dict():
    ctx = _ctx()
    ctx["info_snapshot"] = {}
    text = ds.templated_simulation_note(ctx)
    assert "ClubElo" not in text
    assert "100 matches" in text
