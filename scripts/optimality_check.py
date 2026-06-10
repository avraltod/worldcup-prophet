"""Reviewer fix #2: under (exact=3, result=1) scoring, EV of a pick (h,a) is
3*P(h,a) + 1*(P(outcome)-P(h,a)) = 2*P(h,a) + P(outcome(h,a)).
Check whether the conditional-modal rule's picks match the exact EV argmax
across all 72 group matches."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from poisson_model import fit_rates, pois, MAX_G, outcome_probs

DATA = Path(__file__).parent.parent / "data"
preds = json.loads((DATA / "group_predictions.json").read_text())

mismatches = 0
for p in preds:
    ph, pd, pa = p["p"]
    s = ph + pd + pa
    ph, pd, pa = ph / s, pd / s, pa / s
    lh, la = fit_rates(ph, pd, pa)
    # outcome probs implied by the fitted Poisson (consistent basis for both terms)
    pH_fit, pD_fit, pA_fit = outcome_probs(lh, la)
    out_p = {"H": pH_fit, "D": pD_fit, "A": pA_fit}
    best, best_ev = None, -1.0
    for i in range(MAX_G + 1):
        for j in range(MAX_G + 1):
            o = "H" if i > j else ("D" if i == j else "A")
            ev = 2 * pois(i, lh) * pois(j, la) + out_p[o]
            if ev > best_ev:
                best, best_ev = (i, j, o), ev
    ours = (p["hg"], p["ag"])
    if (best[0], best[1]) != ours:
        mismatches += 1
        print(f'r{p["row"]} {p["home"]} vs {p["away"]}: ours {ours} '
              f'vs EV-argmax {best[:2]} (outcome {best[2]}), '
              f'p(H/D/A)=({ph:.2f},{pd:.2f},{pa:.2f})')
print(f"\n{mismatches}/72 picks differ from the exact (3,1)-EV maximizer")
