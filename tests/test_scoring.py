import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import scoring

ROOT = Path(__file__).resolve().parent.parent
EXP = json.loads((ROOT / "data" / "match_expectations.json").read_text())
M1 = next(m for m in EXP if m["match"] == 1)   # Mexico v South Africa

def test_exact_pick_scores_three():
    r = scoring.score_match(M1["home"], M1["away"], M1["pick"][0], M1["pick"][1])
    assert r["points"] == 3
    assert r["ev_points"] == M1["ev_points"]
    assert 0.0 <= r["brier"] <= 2.0 and 0.0 <= r["p_outcome"] <= 1.0

def test_wrong_result_scores_zero():
    hg, ag = M1["pick"]
    r = scoring.score_match(M1["home"], M1["away"], ag, hg + 3)
    assert isinstance(r["points"], int)
    assert r["points"] in (0, 1, 2, 3)

def test_reversed_pairing_is_oriented():
    r = scoring.score_match(M1["away"], M1["home"], M1["pick"][1], M1["pick"][0])
    assert r["points"] == 3   # same match, reversed input -> still the exact pick

def test_unknown_pairing_returns_none():
    assert scoring.score_match("Mars", "Venus", 1, 0) is None
