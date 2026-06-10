"""Backtest the forecasting pipeline on the 2018 and 2022 World Cups.

For every real match, derive the model's pre-tournament probabilities from
pre-tournament Elo (the same Elo->H/D/A->Poisson pipeline the model uses where
odds are absent), then assess against the actual results:
  - calibration: reliability of the outcome probabilities (binned), plus the
    Brier score and the Ranked Probability Score (RPS) vs a uniform baseline;
  - scoring strategy: points the modal-score (3,1) rule would have earned, vs a
    naive 'always 1-0 for the favorite' baseline.

Format-independent: needs only pre-tournament Elo and the match results, so the
32-team format of 2018/2022 does not matter here.

Run after data/backtest/elo_<year>.json and results_<year>.json exist.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from poisson_model import fit_rates, pois, MAX_G, outcome_probs

DATA = Path(__file__).parent.parent / "data" / "backtest"
HOSTS = {2018: "Russia", 2022: "Qatar"}
ALIAS = {"United States": "USA", "USA": "USA", "Korea Republic": "South Korea",
         "IR Iran": "Iran", "Iran": "Iran", "Czech Republic": "Czechia"}


def look(elo, team):
    if team in elo:
        return elo[team]
    return elo.get(ALIAS.get(team, team))


def elo_hda(ra, rb):
    """Model's Elo -> (P home, P draw, P away), neutral venue."""
    d = ra - rb
    e = 1.0 / (1.0 + 10 ** (-d / 400.0))
    pd_ = 0.30 * math.exp(-abs(d) / 700.0)
    ph = max(0.01, e - pd_ / 2)
    pa = max(0.01, 1.0 - ph - pd_)
    s = ph + pd_ + pa
    return ph / s, pd_ / s, pa / s


def modal_pick(ph, pd_, pa):
    """The (3,1)-optimal scoreline: modal score conditional on modal outcome."""
    lh, la = fit_rates(ph, pd_, pa)
    out = "H" if ph >= pd_ and ph >= pa else ("D" if pd_ >= pa else "A")
    best, bp = (1, 0), -1
    for i in range(MAX_G + 1):
        for j in range(MAX_G + 1):
            ok = (out == "H" and i > j) or (out == "D" and i == j) or (out == "A" and i < j)
            if ok and pois(i, lh) * pois(j, la) > bp:
                best, bp = (i, j), pois(i, lh) * pois(j, la)
    return best, out


def outcome(hg, ag):
    return "H" if hg > ag else ("D" if hg == ag else "A")


def run_year(year):
    elo = json.loads((DATA / f"elo_{year}.json").read_text())
    results = json.loads((DATA / f"results_{year}.json").read_text())
    host = HOSTS[year]
    miss = set()
    brier_model = brier_unif = 0.0
    rps_model = rps_unif = 0.0
    pts_model = pts_naive = 0
    n = 0
    rel = []  # (predicted_prob_of_realized_outcome, 1)
    bins = {}  # confidence bin -> [hits, total] for the model's top pick
    for m in results:
        h, a = m["home"], m["away"]
        eh, ea = look(elo, h), look(elo, a)
        if eh is None or ea is None:
            if eh is None:
                miss.add(h)
            if ea is None:
                miss.add(a)
            continue
        ra = eh + (40 if h == host else 0)
        rb = ea + (40 if a == host else 0)
        ph, pd_, pa = elo_hda(ra, rb)
        p = {"H": ph, "D": pd_, "A": pa}
        real = outcome(m["hg"], m["ag"])
        n += 1

        # Brier (multiclass) and RPS
        for o in ("H", "D", "A"):
            y = 1.0 if o == real else 0.0
            brier_model += (p[o] - y) ** 2
            brier_unif += (1 / 3 - y) ** 2
        # RPS over ordered categories H > D > A (1x2 ordinal)
        order = ["H", "D", "A"]
        cumP = cumO = 0.0
        for o in order:
            cumP += p[o]
            cumO += 1.0 if o == real else 0.0
            rps_model += (cumP - cumO) ** 2
            cu = (order.index(o) + 1) / 3
            rps_unif += (cu - cumO) ** 2

        # calibration: top pick confidence vs whether it hit
        top = max(p, key=p.get)
        conf = p[top]
        b = round(conf * 10) / 10
        bins.setdefault(b, [0, 0])
        bins[b][1] += 1
        if top == real:
            bins[b][0] += 1
        rel.append((p[real], real))

        # scoring strategy
        pick, _ = modal_pick(ph, pd_, pa)
        if (pick[0], pick[1]) == (m["hg"], m["ag"]):
            pts_model += 3
        elif outcome(*pick) == real:
            pts_model += 1
        # naive baseline: 1-0 for the favorite (or 0-0 draw if draw most likely)
        nb = (1, 0) if top == "H" else ((0, 1) if top == "A" else (0, 0))
        if (nb[0], nb[1]) == (m["hg"], m["ag"]):
            pts_naive += 3
        elif outcome(*nb) == real:
            pts_naive += 1

    return {
        "year": year, "n": n, "missing": sorted(miss),
        "brier_model": brier_model / n, "brier_unif": brier_unif / n,
        "rps_model": rps_model / (n * 3), "rps_unif": rps_unif / (n * 3),
        "pts_model": pts_model, "pts_naive": pts_naive,
        "pts_per_match_model": pts_model / n, "pts_per_match_naive": pts_naive / n,
        "bins": {str(k): v for k, v in sorted(bins.items())},
    }


if __name__ == "__main__":
    allr = {}
    for year in (2018, 2022):
        r = run_year(year)
        allr[year] = r
        print(f"=== {year} World Cup backtest ({r['n']} matches) ===")
        if r["missing"]:
            print(f"  WARNING missing Elo for: {r['missing']}")
        print(f"  Brier:  model {r['brier_model']:.3f}  vs uniform {r['brier_unif']:.3f}  "
              f"(lower is better; skill = {(1 - r['brier_model']/r['brier_unif'])*100:.1f}%)")
        print(f"  RPS:    model {r['rps_model']:.3f}  vs uniform {r['rps_unif']:.3f}")
        print(f"  Pool points (3 exact/1 outcome): model {r['pts_model']} "
              f"({r['pts_per_match_model']:.2f}/match) vs naive {r['pts_naive']} "
              f"({r['pts_per_match_naive']:.2f}/match)")
        print("  calibration (top-pick confidence -> actual hit rate):")
        for b, (hit, tot) in r["bins"].items():
            print(f"    predicted ~{float(b)*100:.0f}%: actual {hit}/{tot} = {100*hit/tot:.0f}%")
        print()
    (DATA / "backtest_results.json").write_text(json.dumps(allr, indent=1))
    print("saved data/backtest/backtest_results.json")
