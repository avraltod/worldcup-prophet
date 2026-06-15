import json

import vintages as vin


def _frozen():
    return {"Spain": {"champion": 0.269}, "Argentina": {"champion": 0.181},
            "France": {"champion": 0.143}, "Portugal": {"champion": 0.094},
            "England": {"champion": 0.070}, "Brazil": {"champion": 0.035}}


def test_m000_row():
    r = vin.m000_row(_frozen())
    assert r["edition"] == 0 and r["match"] is None
    assert r["champ_top5"][0] == ["Spain", 0.269]
    assert r["cum_points"] == 0 and r["cum_bits"] == 0.0


def test_upsert_appends_and_replaces(tmp_path, monkeypatch):
    monkeypatch.setattr(vin, "PATH", tmp_path / "v.json")
    vin.upsert(vin.m000_row(_frozen()))
    row1 = {"edition": 1, "match": 1, "fixture": "Mexico v South Africa",
            "result": [2, 0], "points": 1, "cum_points": 1, "mean_brier": 0.166,
            "cum_bits": 0.001, "champ_top5": [["Spain", 0.270]]}
    vin.upsert(row1)
    rows = vin.load()
    assert [r["edition"] for r in rows] == [0, 1]
    vin.upsert({**row1, "cum_points": 1})        # idempotent re-run
    assert len(vin.load()) == 2
    # identical re-upsert of an EARLIER row (with a later edition on disk)
    # must not raise — the real CI re-render path
    row2 = {**row1, "edition": 2, "match": 2, "cum_points": 2}
    vin.upsert(row2)
    vin.upsert(json.loads(json.dumps(row1)))     # disk round-trip equality
    assert len(vin.load()) == 3


def test_upsert_refuses_to_change_earlier_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(vin, "PATH", tmp_path / "v.json")
    vin.upsert(vin.m000_row(_frozen()))
    row1 = {"edition": 1, "match": 1, "fixture": "Mexico v South Africa",
            "result": [2, 0], "points": 1, "cum_points": 1, "mean_brier": 0.166,
            "cum_bits": 0.001, "champ_top5": [["Spain", 0.270]]}
    vin.upsert(row1)
    import pytest
    with pytest.raises(ValueError):
        vin.upsert({"edition": 0, "match": None, "champ_top5": [],
                    "cum_points": 99, "cum_bits": 0.0, "mean_brier": None,
                    "fixture": None, "result": None, "points": None})


def test_latex_table_shows_m000_plus_tail():
    rows = [vin.m000_row(_frozen())] + [
        {"edition": i, "match": i, "fixture": "A v B", "result": [1, 0],
         "points": 1, "cum_points": i, "mean_brier": 0.2, "cum_bits": 0.01 * i,
         "champ_top5": [["Spain", 0.27], ["Argentina", 0.18], ["France", 0.14]]}
        for i in range(1, 25)]
    # pivoted table: rows are editions; max_rows limits how many rows shown
    tex = vin.latex_table(rows, max_rows=9)
    assert "M000" in tex and "M024" in tex    # first and last always present
    assert "M005" not in tex                  # middle editions collapsed out
    assert "Spain" in tex and "tabular" in tex
    assert "longtable" not in tex             # plain table (no float-drop bug)
    assert "Cum." in tex                      # scoring columns present
