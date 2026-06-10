"""Pre-register the model's per-match expectations for the daily experiment.

For each group match: the pick, P(exact pick), P(pick's outcome), expected
points under (3,1) scoring [EV = 2*P(exact) + P(outcome)], and the full
fitted scoreline distribution stats needed for surprise metrics later.
Output: data/match_expectations.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import GROUP_FIXTURES
from poisson_model import fit_rates, pois, MAX_G, outcome_probs

DATA = Path(__file__).parent.parent / "data"
ROW_MATCH = dict(zip(range(4, 76), [
    1, 2, 25, 28, 53, 54,   3, 8, 26, 27, 51, 52,   7, 5, 30, 29, 49, 50,
    4, 6, 31, 32, 59, 60,  10, 9, 34, 33, 56, 55,  11, 12, 36, 35, 58, 57,
    16, 15, 40, 39, 64, 63, 14, 13, 37, 38, 66, 65, 17, 18, 41, 42, 61, 62,
    19, 20, 44, 43, 69, 70, 23, 24, 48, 47, 71, 72, 22, 21, 46, 45, 67, 68]))

preds = {p["row"]: p for p in json.loads((DATA / "group_predictions.json").read_text())}
out = []
total_ev = 0.0
for row, grp, h, a in GROUP_FIXTURES:
    p = preds[row]
    ph, pd_, pa = p["p"]
    s = ph + pd_ + pa
    ph, pd_, pa = ph / s, pd_ / s, pa / s
    lh, la = fit_rates(ph, pd_, pa)
    fH, fD, fA = outcome_probs(lh, la)
    hg, ag = p["hg"], p["ag"]
    p_exact = pois(hg, lh) * pois(ag, la)
    out_pick = "H" if hg > ag else ("D" if hg == ag else "A")
    p_out = {"H": fH, "D": fD, "A": fA}[out_pick]
    ev = 2 * p_exact + p_out
    total_ev += ev
    out.append({
        "match": ROW_MATCH[row], "row": row, "group": grp,
        "home": p["home"], "away": p["away"], "pick": [hg, ag],
        "p_exact": round(p_exact, 4), "p_outcome": round(p_out, 4),
        "ev_points": round(ev, 4), "lh": lh, "la": la,
        "probs_HDA": [round(fH, 4), round(fD, 4), round(fA, 4)],
    })
(DATA / "match_expectations.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(f"72 matches | total expected group-stage points: {total_ev:.1f} "
      f"(avg {total_ev/72:.3f}/match)")
print(f"expected exact hits: {sum(m['p_exact'] for m in out):.1f}")
print(f"expected outcome hits: {sum(m['p_outcome'] for m in out):.1f}")
