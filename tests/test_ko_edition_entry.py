import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ko_edition as ke

def _records(match, pre=True):
    post = {"phase": "post", "match": match, "result": [0, 1], "winner": "Canada",
            "champion": {"France": 0.27}, "champion_b": {"France": 0.3},
            "info_bits": 0.012, "kickoff": "2026-06-28T19:00:00Z"}
    recs = [post]
    if pre:
        recs.insert(0, {"phase": "pre", "match": match, "champion": {"France": 0.26},
                        "champion_b": {"France": 0.29}, "market_champion": {"France": 0.25},
                        "kickoff": "2026-06-28T19:00:00Z"})
    return recs

def test_entry_scores_frozen2_and_contrasts_frozen1():
    f2 = json.loads((ROOT / "data" / "frozen2_entry.json").read_text())["picks"]
    e = ke.build_ko_entry(73, _records(73), f2, actual_home="South Africa",
                          actual_away="Canada")
    assert e["match"] == 73
    assert e["advancer"] == "Canada" and e["frozen2_hit"] is True  # F2 picked Canada
    assert isinstance(e["frozen2_points"], int)
    assert "frozen1_points" in e and "recond_delta" in e  # F2 - F1
    assert e["info_bits"] == 0.012

def test_post_only_when_no_pre_record():
    f2 = json.loads((ROOT / "data" / "frozen2_entry.json").read_text())["picks"]
    e = ke.build_ko_entry(73, _records(73, pre=False), f2,
                          actual_home="South Africa", actual_away="Canada")
    assert e["pre"] is None and e["post_only"] is True


def _pending_records(match, winner="Canada"):
    return [{"phase": "post", "match": match, "result": None,
             "reg_score_pending": True, "decided": "et", "winner": winner,
             "champion": {"France": 0.27}, "champion_b": {}, "info_bits": 0.01,
             "kickoff": "2026-06-28T19:00:00Z"}]


def test_entry_scores_advancer_only_when_pending():
    f2 = json.loads((ROOT / "data" / "frozen2_entry.json").read_text())["picks"]
    e = ke.build_ko_entry(73, _pending_records(73), f2,
                          actual_home="South Africa", actual_away="Canada")
    assert e["reg_score_pending"] is True
    assert e["result"] is None
    # F2 picked Canada to advance -> advancer-only score is 1 (tier 0 + advancer 1)
    assert e["frozen2_hit"] is True and e["frozen2_points"] == 1
    assert e["frozen2_points"] == (1 if e["frozen2_hit"] else 0)


def test_entry_advancer_only_miss_scores_zero():
    f2 = json.loads((ROOT / "data" / "frozen2_entry.json").read_text())["picks"]
    # advancer is South Africa (F2 picked Canada) -> advancer-only miss -> 0
    e = ke.build_ko_entry(73, _pending_records(73, winner="South Africa"), f2,
                          actual_home="South Africa", actual_away="Canada")
    assert e["reg_score_pending"] is True
    assert e["frozen2_hit"] is False and e["frozen2_points"] == 0


def test_entry_normal_post_record_unchanged():
    f2 = json.loads((ROOT / "data" / "frozen2_entry.json").read_text())["picks"]
    e = ke.build_ko_entry(73, _records(73), f2, actual_home="South Africa",
                          actual_away="Canada")
    assert e.get("reg_score_pending") in (None, False)
    assert e["result"] == [0, 1]


def test_render_unit_notes_pending_reg_score():
    e = {"match": 82, "home": "Belgium", "away": "Senegal", "result": None,
         "advancer": "Belgium", "frozen2_points": 1, "frozen1_points": 0,
         "recond_delta": 1, "frozen2_hit": True, "frozen2_pick": {"disp": [2, 1]},
         "frozen1_pick": {"advancer": "Belgium"}, "info_bits": 0.01,
         "champion_after": {}, "pre": None, "post_only": True,
         "reg_score_pending": True}
    tex = ke.render_unit([e])
    assert "pending" in tex.lower() and "90" in tex
    assert "Belgium" in tex and r"\textbf{Total}" in tex


def test_confirm_reg_score_sets_result_and_clears_pending(tmp_path, monkeypatch):
    traj = [{"phase": "post", "match": 82, "result": None, "reg_score_pending": True,
             "decided": "et", "winner": "Belgium", "champion": {"Spain": 0.2},
             "champion_b": {}, "info_bits": 0.01, "kickoff": "2026-07-01T19:00:00Z"}]
    tf = tmp_path / "trajectory_v2.json"
    tf.write_text(json.dumps(traj))
    monkeypatch.setattr(ke, "TRAJ", tf)
    monkeypatch.setattr(ke, "ENTRY_LOG", tmp_path / "ko_edition_log.json")
    monkeypatch.setattr(ke, "_render_and_archive", lambda m: None)
    monkeypatch.setattr(ke, "_realized_pair", lambda m: ("Belgium", "Senegal"))
    f2 = json.loads((ROOT / "data" / "frozen2_entry.json").read_text())["picks"]
    monkeypatch.setattr(ke, "_frozen2", lambda: f2)
    e = ke.confirm_reg_score(82, 2, 2)
    post = [r for r in json.loads(tf.read_text()) if r["phase"] == "post"][0]
    assert post["result"] == [2, 2]
    assert "reg_score_pending" not in post
    assert post["decided"] == "et"                    # decided preserved
    assert e["result"] == [2, 2]
    assert e.get("reg_score_pending") in (None, False)
    # 90' was a 2-2 draw, Belgium won in ET -> tier 0 + advancer 1 = 1
    assert e["frozen2_points"] == 1


def test_scorecard_accumulates_frozen2_and_recond():
    e1 = {"match": 73, "frozen2_points": 3, "frozen1_points": 0, "recond_delta": 3}
    e2 = {"match": 74, "frozen2_points": 4, "frozen1_points": 4, "recond_delta": 0}
    sc = ke.scorecard([e1, e2])
    assert sc["frozen2_total"] == 7 and sc["frozen1_total"] == 4
    assert sc["recond_total"] == 3 and sc["games"] == 2

def test_render_unit_mentions_teams_and_scorecard():
    e = {"match": 73, "home": "South Africa", "away": "Canada", "result": [0, 1],
         "advancer": "Canada", "frozen2_points": 3, "frozen1_points": 0,
         "recond_delta": 3, "frozen2_hit": True, "frozen2_pick": {"disp": [1, 2]},
         "frozen1_pick": {"advancer": "Canada"}, "info_bits": 0.01,
         "champion_after": {"France": 0.27}, "pre": None, "post_only": True}
    tex = ke.render_unit([e])
    assert "Canada" in tex and "Frozen" in tex and "knockout" in tex.lower()
    assert r"\textbf{Total}" in tex
    assert r"\bottomrule" in tex


def test_issue_appends_entry_and_marks(tmp_path, monkeypatch):
    monkeypatch.setattr(ke, "ENTRY_LOG", tmp_path / "ko_edition_log.json")
    monkeypatch.setattr(ke, "_render_and_archive", lambda m: None)  # skip TeX
    traj = [{"phase": "post", "match": 73, "result": [0, 1], "winner": "Canada",
             "champion": {"France": 0.27}, "champion_b": {}, "info_bits": 0.01,
             "kickoff": "2026-06-28T19:00:00Z"}]
    monkeypatch.setattr(ke, "_trajectory", lambda: traj)
    monkeypatch.setattr(ke, "_realized_pair", lambda m: ("South Africa", "Canada"))
    e = ke.issue(73)
    assert e["match"] == 73 and e["advancer"] == "Canada"
    import json
    assert json.loads((tmp_path / "ko_edition_log.json").read_text())[0]["match"] == 73
    ke.issue(73)  # issuing again must not duplicate
    import json as _json
    log = _json.loads((tmp_path / "ko_edition_log.json").read_text())
    assert [e["match"] for e in log] == [73]


def test_build_ko_entry_reorients_flipped_scoreline():
    # France won 1-0 but the recorder stored the scoreline flipped as [0,1]
    # (ESPN orientation); winner=France is authoritative.
    records = [{"phase": "post", "match": 95, "result": [0, 1], "winner": "France"}]
    picks = {"95": {"home": "France", "away": "Paraguay", "disp": [2, 0],
                    "advancer": "France"}}
    e = ke.build_ko_entry(95, records, picks, "France", "Paraguay")
    assert e["result"] == [1, 0]            # oriented to (home=France, away)
    # France won by 1 vs predicted win by 2: result tier (1) + advancer (1) = 2
    assert e["frozen2_points"] == 2


def test_build_ko_entry_orientation_noop_when_already_correct():
    records = [{"phase": "post", "match": 95, "result": [1, 0], "winner": "France"}]
    picks = {"95": {"home": "France", "away": "Paraguay", "disp": [2, 0],
                    "advancer": "France"}}
    e = ke.build_ko_entry(95, records, picks, "France", "Paraguay")
    assert e["result"] == [1, 0] and e["frozen2_points"] == 2


def test_build_ko_entry_draw_is_orientation_immune():
    records = [{"phase": "post", "match": 95, "result": [1, 1], "winner": "France"}]
    picks = {"95": {"home": "France", "away": "Paraguay", "disp": [1, 1],
                    "advancer": "France"}}
    e = ke.build_ko_entry(95, records, picks, "France", "Paraguay")
    assert e["result"] == [1, 1]
