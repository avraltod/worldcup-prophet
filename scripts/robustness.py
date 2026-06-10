"""Referee-requested robustness checks (no new data needed).

B6 Shin de-vigging vs basic normalization: does the choice change any of the 72
   group picks? (Strumbelj 2014 shows Shin dominates; reviewers want the picks,
   not the likelihood.)
B5 Dixon-Coles low-score correction: does it change any pick or the backtested
   points? (Reviewers: test the decision, not the in-sample log-likelihood.)
B7 Poisson fit diagnostics: how often does the lambda-sum box constraint bind,
   and what is the mean H/D/A fitting residual?
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from poisson_model import fit_rates, pois, MAX_G, outcome_probs
from ev321 import best_pick

DATA = Path(__file__).parent.parent / "data"


def shin_devig(oh, od, oa):
    """Shin (1993) de-vig for a 3-outcome book. Returns fair (pH,pD,pA)."""
    b = [1.0 / oh, 1.0 / od, 1.0 / oa]
    B = sum(b)
    def p_of_z(z):
        return [(math.sqrt(z * z + 4 * (1 - z) * bi * bi / B) - z) / (2 * (1 - z)) for bi in b]
    lo, hi = 0.0, 0.5
    for _ in range(60):
        z = (lo + hi) / 2
        s = sum(p_of_z(z))
        if s > 1:
            lo = z
        else:
            hi = z
    p = p_of_z((lo + hi) / 2)
    s = sum(p)
    return [x / s for x in p]


def dc_tau(i, j, lh, la, rho):
    if i == 0 and j == 0:
        return 1 - lh * la * rho
    if i == 0 and j == 1:
        return 1 + lh * rho
    if i == 1 and j == 0:
        return 1 + la * rho
    if i == 1 and j == 1:
        return 1 - rho
    return 1.0


def best_pick_dc(lh, la, rho):
    def ev(h, a):
        gp, rp = h - a, (h > a) - (h < a)
        pe = pois(h, lh) * pois(a, la) * dc_tau(h, a, lh, la, rho)
        prg = pr = 0.0
        for i in range(MAX_G + 1):
            for j in range(MAX_G + 1):
                p = pois(i, lh) * pois(j, la) * dc_tau(i, j, lh, la, rho)
                r = (i > j) - (i < j)
                if r == rp:
                    pr += p
                    if i - j == gp:
                        prg += p
        return pe + prg + pr
    best, bev = (1, 0), -1
    for h in range(MAX_G + 1):
        for a in range(MAX_G + 1):
            e = ev(h, a)
            if e > bev:
                best, bev = (h, a), e
    return best


def main():
    preds = json.loads((DATA / "group_predictions.json").read_text())
    odds = {}
    for f in ("odds_AD", "odds_EH", "odds_IL"):
        for r in json.loads((DATA / f"{f}.json").read_text()):
            if "odds_home" in r:
                odds[(r["home"], r["away"])] = (r["odds_home"], r["odds_draw"], r["odds_away"])

    # B6 Shin vs basic
    shin_changes = 0
    n_with_odds = 0
    # B7 GOF
    n_bind = 0
    resid = []
    # B5 DC
    dc_changes = {0.1: 0, -0.1: 0}

    for p in preds:
        pb = p["p"]
        s = sum(pb)
        pb = [x / s for x in pb]
        lh, la = fit_rates(*pb)
        cur = best_pick(lh, la)

        # B7 goodness of fit
        if abs((lh + la) - 1.6) < 1e-3 or abs((lh + la) - 3.4) < 1e-3:
            n_bind += 1
        fH, fD, fA = outcome_probs(lh, la)
        resid.append(math.sqrt(((fH - pb[0]) ** 2 + (fD - pb[1]) ** 2 + (fA - pb[2]) ** 2) / 3))

        # B6 Shin
        key = (p["home"], p["away"])
        if key in odds:
            n_with_odds += 1
            ps = shin_devig(*odds[key])
            ls = fit_rates(*ps)
            if best_pick(*ls) != cur:
                shin_changes += 1

        # B5 Dixon-Coles
        for rho in (0.1, -0.1):
            if best_pick_dc(lh, la, rho) != cur:
                dc_changes[rho] += 1

    print("=== B6 Shin de-vig vs basic normalization (2026 group picks) ===")
    print(f"  fixtures with raw odds: {n_with_odds}/72")
    print(f"  picks that change under Shin de-vig: {shin_changes}/{n_with_odds}")
    print("\n=== B7 Poisson fit diagnostics ===")
    print(f"  lambda-sum constraint binds: {n_bind}/72 fixtures")
    print(f"  mean RMS H/D/A fitting residual: {sum(resid)/len(resid):.4f} "
          f"(max {max(resid):.4f})")
    print("\n=== B5 Dixon-Coles pick changes ===")
    print(f"  picks changed at rho=+0.10: {dc_changes[0.1]}/72")
    print(f"  picks changed at rho=-0.10: {dc_changes[-0.1]}/72")


if __name__ == "__main__":
    main()
