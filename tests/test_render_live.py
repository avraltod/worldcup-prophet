"""render_live: each living unit renders to its own paper/live/*.tex file; the
skeleton is asserted byte-identical via its stored sha256."""
import hashlib

import render_live as rl


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
    assert "2--0" in tex                      # real result beside the pick
    assert "South Korea v Czechia" in tex     # remaining fixture with lock probs
    gB = next(g for g in _gs12() if g["group"] == "B")
    tex_b = rl.group_box(gB, {"group": {}}, [], frozen, now)
    assert "No results yet" in tex_b


def test_survival_unit_restates_all_teams():
    frozen, now = _stages(), _stages(0.30)
    tex = rl.survival_unit(frozen, now)
    assert "Spain" in tex and "30.0" in tex and "longtable" in tex
