"""Pure per-match scoring (pool 3/2/1 + Brier), reused by the v2 recorder without
touching v1's ledger. Mirrors score_day.py's formula; reads match_expectations.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import canon
from poisson_model import pois  # noqa: F401  (imported for parity; brier uses probs_HDA)

ROOT = Path(__file__).resolve().parent.parent
_EXP = json.loads((ROOT / "data" / "match_expectations.json").read_text())
_BY_PAIR = {(m["home"], m["away"]): m for m in _EXP}


def _outcome(hg, ag):
    return "H" if hg > ag else ("D" if hg == ag else "A")


def score_match(home, away, hg, ag):
    """Return {points, ev_points, p_outcome, brier} for a group match (inputs oriented
    to the given home/away), or None if the pairing is not a known group fixture."""
    key = (canon(home), canon(away))
    m = _BY_PAIR.get(key)
    if m is None:
        m = _BY_PAIR.get((key[1], key[0]))
        if m is None:
            return None
        hg, ag = ag, hg  # orient to the fixture's home/away
    pick = m["pick"]
    real_out, pick_out = _outcome(hg, ag), _outcome(*pick)
    if [hg, ag] == pick:
        pts = 3
    elif real_out == pick_out and (hg - ag) == (pick[0] - pick[1]):
        pts = 2
    elif real_out == pick_out:
        pts = 1
    else:
        pts = 0
    p_out = m["probs_HDA"]["HDA".index(real_out)]
    brier = sum((p - (1.0 if "HDA"[i] == real_out else 0.0)) ** 2
                for i, p in enumerate(m["probs_HDA"]))
    return {"points": pts, "ev_points": m["ev_points"],
            "p_outcome": round(p_out, 4), "brier": round(brier, 4)}
