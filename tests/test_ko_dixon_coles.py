"""Reproducibility guard for the Dixon-Coles robustness conclusion (peer-review
item M3): adding a low-score (DC) correlation correction does NOT change any
EV-optimal 90' scoreline across the optimal bracket's matchups, so the
independent-Poisson assumption in the KO scoreline optimizer is vindicated.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ko_repick as kr
import ko_match_ev as kme
import ev321
from poisson_model import pois, MAX_G


def _dc_tau(i, j, lh, la, rho):
    """Dixon-Coles low-score correction factor (1 elsewhere)."""
    if i == 0 and j == 0:
        return 1 - lh * la * rho
    if i == 0 and j == 1:
        return 1 + lh * rho
    if i == 1 and j == 0:
        return 1 + la * rho
    if i == 1 and j == 1:
        return 1 - rho
    return 1.0


def _dc_best_pick(lh, la, rho):
    """EV-optimal 3/2/1 scoreline under a DC-corrected, renormalized joint."""
    grid = [[pois(i, lh) * pois(j, la) * _dc_tau(i, j, lh, la, rho)
             for j in range(MAX_G + 1)] for i in range(MAX_G + 1)]
    z = sum(sum(row) for row in grid)
    best, bev = (1, 0), -1.0
    for h in range(MAX_G + 1):
        for a in range(MAX_G + 1):
            gp, rp = h - a, (h > a) - (h < a)
            p_exact = grid[h][a] / z
            p_rg = p_r = 0.0
            for i in range(MAX_G + 1):
                for j in range(MAX_G + 1):
                    p = grid[i][j] / z
                    r = (i > j) - (i < j)
                    if r == rp:
                        p_r += p
                        if i - j == gp:
                            p_rg += p
            ev = p_exact + p_rg + p_r
            if ev > bev:
                best, bev = (h, a), ev
    return best


def _predicted_results():
    pr = json.loads((ROOT / "data" / "predictions_realistic.json").read_text())
    groups = {str(p["num"]): [p["hg"], p["ag"]]
              for p in pr if str(p["stage"]).startswith("Group")}
    return {"group": groups, "ko": {}}


def test_dixon_coles_does_not_change_any_scoreline_pick():
    eff = kme.load_live_eff()
    entry = kr.optimize_entry(_predicted_results(), eff=eff, N=2000, seed=1)
    pairs = [(p["home"], p["away"]) for p in entry["picks"].values()]
    for rho in (0.05, 0.10, 0.15):
        flips = 0
        for home, away in pairs:
            lh, la = kme.matchup_lambdas(home, away, eff)
            if ev321.best_pick(lh, la) != _dc_best_pick(lh, la, rho):
                flips += 1
        assert flips == 0, f"rho={rho}: {flips} scoreline picks changed under DC"
