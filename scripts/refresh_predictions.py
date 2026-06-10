"""Refresh predictions from updated odds (data/odds_refresh.json).

For each refreshed fixture: recompute the (3,1)-EV-optimal pick, compare with
the current submitted pick (group_predictions.json + the r26 flip), and report
changes. Writes data/group_predictions_v2.json with updates applied.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import GROUP_FIXTURES, canon
from poisson_model import fit_rates, pois, MAX_G, outcome_probs

DATA = Path(__file__).parent.parent / "data"

preds = json.loads((DATA / "group_predictions.json").read_text())
by_row = {p["row"]: p for p in preds}
by_row[26]["hg"], by_row[26]["ag"] = 0, 1  # submitted r26 flip
ROW_BY_PAIR = {(canon(h), canon(a)): r for r, g, h, a in GROUP_FIXTURES}

refresh = json.loads((DATA / "odds_refresh.json").read_text())
changes, confirmed, missing = [], [], []
for m in refresh:
    if m.get("found") is False:
        missing.append(f'{m["home"]} vs {m["away"]}')
        continue
    key = (canon(m["home"]), canon(m["away"]))
    row = ROW_BY_PAIR.get(key) or ROW_BY_PAIR.get((key[1], key[0]))
    if row is None:
        print(f"!! cannot map {key}")
        continue
    p = by_row[row]
    rev = canon(m["home"]) != p["home"]
    ph, pd, pa = (m["p_away"], m["p_draw"], m["p_home"]) if rev else \
                 (m["p_home"], m["p_draw"], m["p_away"])
    s = ph + pd + pa
    ph, pd, pa = ph / s, pd / s, pa / s
    lh, la = fit_rates(ph, pd, pa)
    pH_f, pD_f, pA_f = outcome_probs(lh, la)
    out_p = {"H": pH_f, "D": pD_f, "A": pA_f}
    best, best_ev = None, -1.0
    for i in range(MAX_G + 1):
        for j in range(MAX_G + 1):
            o = "H" if i > j else ("D" if i == j else "A")
            ev = 2 * pois(i, lh) * pois(j, la) + out_p[o]
            if ev > best_ev:
                best, best_ev = (i, j), ev
    old = (p["hg"], p["ag"])
    entry = {"row": row, "home": p["home"], "away": p["away"],
             "old": old, "new": best,
             "p_new": [round(ph, 3), round(pd, 3), round(pa, 3)],
             "source": m.get("source", "")}
    if best != old:
        changes.append(entry)
        p["hg"], p["ag"] = best
        p["p"] = entry["p_new"]
        p["source"] = m.get("source", "") + " [refresh 06-07]"
    else:
        confirmed.append(entry)

(DATA / "group_predictions_v2.json").write_text(
    json.dumps(preds, ensure_ascii=False, indent=1))

print(f"=== {len(changes)} PICK CHANGES ===")
for c in changes:
    print(f'r{c["row"]} {c["home"]} vs {c["away"]}: {c["old"][0]}-{c["old"][1]} '
          f'-> {c["new"][0]}-{c["new"][1]}  p={c["p_new"]}  ({c["source"]})')
print(f"\n=== {len(confirmed)} picks confirmed by market ===")
for c in confirmed:
    print(f'r{c["row"]} {c["home"]} vs {c["away"]}: stays {c["old"][0]}-{c["old"][1]} p={c["p_new"]}')
if missing:
    print(f"\n=== still unpublished: {missing}")
