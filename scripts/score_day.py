"""Daily experiment scorer.

Usage:
  python3 scripts/score_day.py '<json>'
  echo '<json>' | python3 scripts/score_day.py -

Input JSON: [{"home":"Mexico","away":"South Africa","hg":2,"ag":0}, ...]
(90-minute scores; team names as in the prediction sheet, aliases OK)

Outputs per match: points, EV, surprises, Brier, diagnosis-code suggestion;
appends to experiment/ledger.csv and prints a ready-to-paste diary row.
"""
import csv
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import canon
from poisson_model import pois

ROOT = Path(__file__).parent.parent
EXP = json.loads((ROOT / "data" / "match_expectations.json").read_text())
BY_PAIR = {(m["home"], m["away"]): m for m in EXP}
LEDGER = ROOT / "experiment" / "ledger.csv"


def outcome(hg, ag):
    return "H" if hg > ag else ("D" if hg == ag else "A")


def main():
    raw = sys.stdin.read() if sys.argv[1] == "-" else sys.argv[1]
    results = json.loads(raw)
    new_rows = []
    day_pts = day_ev = day_brier = 0.0
    print(f"{'match':<42} {'pred':>5} {'real':>5} {'pts':>3} {'EV':>5} "
          f"{'P(out)':>6} {'P(score)':>8} code?")
    for r in results:
        key = (canon(r["home"]), canon(r["away"]))
        m = BY_PAIR.get(key)
        rev = False
        if m is None:
            m = BY_PAIR.get((key[1], key[0]))
            rev = True
        if m is None:
            print(f"!! {key} not a group fixture (knockout matches: score manually "
                  f"against the bracket; matchup must match)")
            continue
        hg, ag = (r["ag"], r["hg"]) if rev else (r["hg"], r["ag"])
        pick = m["pick"]
        real_out, pick_out = outcome(hg, ag), outcome(*pick)
        # pool scoring: 3 exact, 2 result+GD, 1 result only
        if [hg, ag] == pick:
            pts = 3
        elif real_out == pick_out and (hg - ag) == (pick[0] - pick[1]):
            pts = 2
        elif real_out == pick_out:
            pts = 1
        else:
            pts = 0
        p_realout = m["probs_HDA"]["HDA".index(real_out)]
        p_realscore = pois(hg, m["lh"]) * pois(ag, m["la"])
        brier = sum((p - (1.0 if "HDA"[i] == real_out else 0.0)) ** 2
                    for i, p in enumerate(m["probs_HDA"]))
        # diagnosis suggestion (final call is human)
        if pts == 3:
            code = "HIT"
        elif pts == 1:
            code = "S"
        else:
            code = "L?" if p_realout < 0.25 else "P?"
        day_pts += pts
        day_ev += m["ev_points"]
        day_brier += brier
        print(f"M{m['match']:<3} {m['home']} vs {m['away']:<24} "
              f"{pick[0]}-{pick[1]:>2} {hg}-{ag:>2} {pts:>3} {m['ev_points']:>5.2f} "
              f"{p_realout:>6.2f} {p_realscore:>8.3f} {code}")
        new_rows.append([date.today().isoformat(), m["match"], m["home"], m["away"],
                         f"{pick[0]}-{pick[1]}", f"{hg}-{ag}", pts,
                         m["ev_points"], round(p_realout, 3),
                         round(p_realscore, 4), round(brier, 4), code])
    n = len(new_rows)
    if not n:
        return
    write_header = not LEDGER.exists()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["date", "match", "home", "away", "pred", "actual",
                        "pts", "ev", "p_outcome_real", "p_score_real",
                        "brier", "code"])
        w.writerows(new_rows)
    # cumulative
    rows = list(csv.DictReader(LEDGER.open()))
    cum_pts = sum(int(r["pts"]) for r in rows)
    cum_ev = sum(float(r["ev"]) for r in rows)
    cum_brier = sum(float(r["brier"]) for r in rows) / len(rows)
    exact = sum(1 for r in rows if r["pts"] == "3")
    print(f"\nDAY: {day_pts:.0f} pts vs {day_ev:.2f} expected "
          f"({'+' if day_pts >= day_ev else ''}{day_pts - day_ev:.2f})")
    print(f"CUMULATIVE ({len(rows)} matches): {cum_pts} pts vs {cum_ev:.1f} EV | "
          f"exact hits {exact} | avg Brier {cum_brier:.3f} (H5 target <=0.60)")
    print(f"\nDiary row:\n| {date.today().strftime('%b %d')} | {n} matches | "
          f"{day_pts:.0f} / {3*n} | <fill: what went wrong, codes> | <bracket notes> |")


if __name__ == "__main__":
    main()
