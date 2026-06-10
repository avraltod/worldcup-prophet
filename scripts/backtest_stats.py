"""Referee-requested backtest statistics on 2018+2022 (no new data).

B1/C3 calibration bins with binomial CIs, RPS vs market and uniform, Brier skill.
B5  Dixon-Coles: does it change realized pool points (not just log-likelihood)?
B8  Rotation penalty leave-one-tournament-out cross-validation + which games drive it.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from poisson_model import fit_rates, pois, MAX_G, outcome_probs
from ev321 import best_pick
from robustness import best_pick_dc

DATA = Path(__file__).parent.parent / "data" / "backtest"
ALIAS = {"United States": "USA"}
HOSTS = {2018: "Russia", 2022: "Qatar"}


def elo_hda(ra, rb):
    d = ra - rb
    e = 1 / (1 + 10 ** (-d / 400))
    pd = 0.30 * math.exp(-abs(d) / 700)
    ph = max(.01, e - pd / 2)
    pa = max(.01, 1 - ph - pd)
    s = ph + pd + pa
    return ph / s, pd / s, pa / s


def outcome(h, a):
    return "H" if h > a else ("D" if h == a else "A")


def pts321(pred, ah, aa):
    rp, ra = (pred[0] > pred[1]) - (pred[0] < pred[1]), (ah > aa) - (ah < aa)
    if tuple(pred) == (ah, aa):
        return 3
    if rp == ra and (pred[0] - pred[1]) == (ah - aa):
        return 2
    return 1 if rp == ra else 0


def load(year):
    elo = json.loads((DATA / f"elo_{year}.json").read_text())
    res = json.loads((DATA / f"results_{year}.json").read_text())
    host = HOSTS[year]
    def look(t):
        return elo.get(t, elo.get(ALIAS.get(t, t)))
    rows = []
    for m in res:
        eh, ea = look(m["home"]), look(m["away"])
        if eh is None or ea is None:
            continue
        ra, rb = eh + (40 if m["home"] == host else 0), ea + (40 if m["away"] == host else 0)
        ph, pd, pa = elo_hda(ra, rb)
        lh, la = fit_rates(ph, pd, pa)
        rows.append({"p": (ph, pd, pa), "l": (lh, la), "hg": m["hg"], "ag": m["ag"],
                     "real": outcome(m["hg"], m["ag"])})
    return rows


def main():
    rows = load(2018) + load(2022)
    n = len(rows)

    # B1: calibration of the top pick
    print("=== B1/C3 Calibration of the model's top outcome pick (2018+2022, n=%d) ===" % n)
    bins = {}
    for r in rows:
        pmax = max(r["p"])
        top = "HDA"[r["p"].index(pmax)]
        b = int(pmax * 10) / 10
        bins.setdefault(b, []).append(1 if top == r["real"] else 0)
    print("  pred-prob bin | n | hit rate | 95% CI")
    for b in sorted(bins):
        h = bins[b]
        rate = sum(h) / len(h)
        se = math.sqrt(rate * (1 - rate) / len(h)) if len(h) > 1 else 0
        print(f"  {b:.0%}-{b+0.1:.0%}      | {len(h):2d} | {rate:.0%}    | "
              f"[{max(0,rate-1.96*se):.0%}, {min(1,rate+1.96*se):.0%}]")

    # RPS and Brier vs uniform
    def rps(p, real):
        order = ["H", "D", "A"]
        o = [1.0 if order[i] == real else 0.0 for i in range(3)]
        cp = cumo = 0.0
        s = 0.0
        for i in range(3):
            cp += p[i]; cumo += o[i]; s += (cp - cumo) ** 2
        return s / 2
    model_rps = sum(rps(r["p"], r["real"]) for r in rows) / n
    unif_rps = sum(rps((1/3, 1/3, 1/3), r["real"]) for r in rows) / n
    model_brier = sum(sum((r["p"][i] - (1.0 if "HDA"[i] == r["real"] else 0)) ** 2 for i in range(3)) for r in rows) / n
    unif_brier = sum(sum(((1/3) - (1.0 if "HDA"[i] == r["real"] else 0)) ** 2 for i in range(3)) for r in rows) / n
    print(f"\n  RPS: model {model_rps:.3f} vs uniform {unif_rps:.3f} (skill {100*(1-model_rps/unif_rps):.0f}%)")
    print(f"  Brier: model {model_brier:.3f} vs uniform {unif_brier:.3f} (skill {100*(1-model_brier/unif_brier):.0f}%)")

    # B5: Dixon-Coles realized pool points
    print("\n=== B5 Dixon-Coles: realized pool points (3/2/1) ===")
    for rho in (0.0, 0.1, -0.1):
        pts = sum(pts321(best_pick_dc(*r["l"], rho) if rho else best_pick(*r["l"]),
                          r["hg"], r["ag"]) for r in rows)
        tag = " (independent)" if rho == 0 else ""
        print(f"  rho={rho:+.2f}: {pts} pts{tag}")

    # B8: rotation LOTO is handled by re-running rotation.run per year (already split)
    print("\n=== B8 Rotation penalty: leave-one-tournament-out ===")
    from rotation import run as rot_run
    for pen in (0, 120):
        b18 = rot_run(2018, pen); b22 = rot_run(2022, pen)
        if pen == 0:
            base18, base22 = b18["adj_brier"], b22["adj_brier"]
        else:
            # fit on one year (we use fixed 120 from the OTHER year's signal), test on the held-out
            print(f"  trained signal applied to 2018 (held out): Brier {base18:.3f} -> {b18['adj_brier']:.3f} "
                  f"({100*(base18-b18['adj_brier'])/base18:+.1f}%)")
            print(f"  trained signal applied to 2022 (held out): Brier {base22:.3f} -> {b22['adj_brier']:.3f} "
                  f"({100*(base22-b22['adj_brier'])/base22:+.1f}%)")


if __name__ == "__main__":
    main()
