"""Auto-score completed group matches into experiment/ledger.csv.

Reads results from data/results_log_v2.json, skips matches already in the
ledger, and appends new rows. Designed to run from CI after live_update_v2.py.
"""
import csv
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from poisson_model import pois

ROOT = Path(__file__).resolve().parent.parent
EXP = json.loads((ROOT / "data" / "match_expectations.json").read_text())
BY_MATCH = {m["match"]: m for m in EXP}
LEDGER = ROOT / "experiment" / "ledger.csv"
RESULTS_V2 = ROOT / "data" / "results_log_v2.json"

HEADER = ["date", "match", "home", "away", "pred", "actual",
          "pts", "ev", "p_outcome_real", "p_score_real", "brier", "code"]


def _outcome(hg, ag):
    return "H" if hg > ag else ("D" if hg == ag else "A")


def _already_scored():
    if not LEDGER.exists():
        return set()
    with LEDGER.open() as f:
        return {int(r["match"]) for r in csv.DictReader(f)}


def _score_row(match_num, hg, ag, today):
    m = BY_MATCH.get(match_num)
    if m is None:
        print(f"!! match {match_num} not in expectations, skipping")
        return None
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
    p_realout = m["probs_HDA"]["HDA".index(real_out)]
    p_realscore = pois(hg, m["lh"]) * pois(ag, m["la"])
    brier = sum((p - (1.0 if "HDA"[i] == real_out else 0.0)) ** 2
                for i, p in enumerate(m["probs_HDA"]))
    if pts == 3:
        code = "HIT"
    elif pts == 1:
        code = "S"
    else:
        code = "L?" if p_realout < 0.25 else "P?"
    print(f"M{match_num:>3} {m['home']} vs {m['away']}: "
          f"{pick[0]}-{pick[1]} → {hg}-{ag} = {pts}pt ({code})")
    return [today, match_num, m["home"], m["away"],
            f"{pick[0]}-{pick[1]}", f"{hg}-{ag}", pts,
            round(m["ev_points"], 4), round(p_realout, 4),
            round(p_realscore, 4), round(brier, 4), code]


def main():
    if not RESULTS_V2.exists():
        print("auto_score: results_log_v2.json not found, nothing to do.")
        return

    raw = json.loads(RESULTS_V2.read_text())
    group_results = dict(raw).get("group", {})  # {"1": [hg,ag], ...}

    scored = _already_scored()
    today = date.today().isoformat()
    new_rows = []

    for match_str, (hg, ag) in sorted(group_results.items(), key=lambda x: int(x[0])):
        match_num = int(match_str)
        if match_num in scored:
            continue
        row = _score_row(match_num, hg, ag, today)
        if row:
            new_rows.append(row)

    if not new_rows:
        print("auto_score: ledger already up to date.")
        return

    write_header = not LEDGER.exists()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(HEADER)
        w.writerows(new_rows)

    print(f"auto_score: appended {len(new_rows)} new row(s) to {LEDGER.name}")


if __name__ == "__main__":
    main()
