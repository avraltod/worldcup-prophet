from collect_match import parse_statistics

# real shape from get_event_statistics (2022 WC match 633790), away made-up but valid
RAW = {
    "status": True,
    "data": {"teams": [
        {"team": {"name": "Qatar"}, "qualifier": "home",
         "statistics": {"ball_possession": "47.1", "shots_total": "0",
            "shots_on_target": "0", "shots_off_target": "0", "shots_blocked": "0",
            "corner_kicks": "1", "fouls": "15", "offsides": "3",
            "yellow_cards": "4", "red_cards": "0", "passes_total": "434"}},
        {"team": {"name": "Ecuador"}, "qualifier": "away",
         "statistics": {"ball_possession": "52.9", "shots_total": "6",
            "shots_on_target": "3", "shots_off_target": "2", "shots_blocked": "1",
            "corner_kicks": "5", "fouls": "11", "offsides": "1",
            "yellow_cards": "2", "red_cards": "0", "passes_total": "500"}},
    ]},
}

def test_parse_converts_strings_to_numbers_and_keys():
    out = parse_statistics(RAW)
    assert out["home"]["team"] == "Qatar"
    assert out["home"]["possession"] == 47.1      # float kept
    assert out["home"]["shots"] == 0              # int
    assert out["away"]["sot"] == 3
    assert out["away"]["corners"] == 5

def test_other_shots_is_offtarget_plus_blocked():
    out = parse_statistics(RAW)
    assert out["away"]["other_shots"] == 3        # 2 off-target + 1 blocked
    assert out["home"]["other_shots"] == 0

def test_missing_or_empty_value_becomes_zero():
    raw = {"data": {"teams": [
        {"team": {"name": "X"}, "qualifier": "home",
         "statistics": {"shots_on_target": "", "shots_total": "4"}},
        {"team": {"name": "Y"}, "qualifier": "away", "statistics": {}},
    ]}}
    out = parse_statistics(raw)
    assert out["home"]["sot"] == 0
    assert out["away"]["shots"] == 0

def test_nonnumeric_value_becomes_zero():
    # real free feeds occasionally emit placeholders like 'N/A' or '-'
    raw = {"data": {"teams": [
        {"team": {"name": "X"}, "qualifier": "home",
         "statistics": {"shots_total": "N/A", "shots_on_target": "-"}},
        {"team": {"name": "Y"}, "qualifier": "away", "statistics": {}},
    ]}}
    out = parse_statistics(raw)
    assert out["home"]["shots"] == 0
    assert out["home"]["sot"] == 0
