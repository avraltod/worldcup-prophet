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


def test_templated_abstract_live_delta_framing_and_bits_pct():
    # New: delta framing (frozen → Track A) and bits as % of max, no Brier
    text = ds.templated_abstract_live(_ctx())
    assert "from" in text           # delta framing "from X% to Y%"
    assert "%" in text              # bits pct of max
    assert "0.003 bits" in text or "bits" in text   # bits value present
    assert "0.52" not in text       # Brier moved out of abstract


def test_templated_abstract_live_track_b_when_present():
    ctx = _ctx()
    ctx["champ_b_top"] = [("Spain", 0.275), ("Argentina", 0.182)]
    text = ds.templated_abstract_live(ctx)
    assert "Track~B" in text and "27.5" in text


def test_templated_intro_data_note_track_a_and_track_b():
    text = ds.templated_intro_data_note(_ctx())
    assert "Track~A" in text and "Track~B" in text
    assert "ClubElo" in text


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


def test_templated_sec36_live_hypothesis_status():
    text = ds.templated_sec36_live(_ctx())
    assert "H1" in text and "H2" in text and "H3" in text


def test_templated_sec36_live_track_ab_naming():
    text = ds.templated_sec36_live(_ctx())
    assert "Track~A" in text or "Track~B" in text


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


def test_templated_discussion_live_four_beats():
    text = ds.templated_discussion_live(_ctx())
    # Beat 1: position
    assert "leads at" in text
    # Beat 2: performance
    assert "pool points" in text or "Brier" in text
    # Beat 3: at-risk call
    assert any(t in text for t in ["Norway", "Croatia", "Belgium", "United States"])
    # Beat 4: key question / H-hypothesis
    assert "H1" in text or "H3" in text or "concentration" in text


def test_templated_robustness_live_uses_track_a_probs():
    ctx = _ctx()
    # United States has known advance_KO in ctx["now"]
    text = ds.templated_robustness_live(ctx)
    # Should mention advance probability for United States (in now dict)
    assert "Norway" in text and "Croatia" in text and "Belgium" in text
    # Should mention verdict (confirmed / at risk / flipped)
    assert any(v in text for v in ["confirmed", "at risk", "flipped"])


def test_templated_failure_analysis_no_boilerplate():
    ctx = _ctx()
    ctx["entries"][1]["post"]["brier"] = 0.52
    text = ds.templated_failure_analysis(ctx)
    assert "documented failure case for post-tournament analysis" not in text


def test_draft_abstract_live_falls_back_to_template_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text, source = ds.draft_abstract_live(_ctx(), use_api=True)
    assert source == "template"
    assert "Spain" in text


def test_templated_simulation_note_v2_pure_methodology():
    # Data state must NOT appear in simulation_note (it moved to data_revealed)
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
    assert "Track~A" in text and "Track~B" in text
    assert "ClubElo" in text                           # methodology still present
    assert "2026-06-13" not in text                    # date state NOT in sim note
    assert "12.3" not in text                          # rms delta NOT in sim note
    assert "100" in text                               # remaining matches still in Para 1
    assert "50,000" in text or "50{,}000" in text      # N draws stated in Para 2


def test_templated_simulation_note_always_two_paras():
    # Both paragraphs always present regardless of info_snapshot
    ctx = _ctx()
    text = ds.templated_simulation_note(ctx)
    assert "Track~A" in text and "Track~B" in text
    assert "ClubElo" in text
    assert "\n\n" in text                              # two paragraphs always
