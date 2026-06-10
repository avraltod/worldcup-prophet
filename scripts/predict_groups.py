"""Merge odds JSONs, compute modal exact scores for all 72 group matches,
emit predictions JSON + a human-readable table."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import GROUP_FIXTURES, canon
from poisson_model import modal_score

DATA = Path(__file__).parent.parent / "data"


def load_odds():
    by_pair = {}
    for f in ["odds_AD.json", "odds_EH.json", "odds_IL.json"]:
        for m in json.loads((DATA / f).read_text()):
            key = (canon(m["home"]), canon(m["away"]))
            by_pair[key] = m
    return by_pair


def main():
    odds = load_odds()
    out, missing = [], []
    for row, grp, home, away in GROUP_FIXTURES:
        m = odds.get((home, away)) or odds.get((away, home))
        if m is None:
            missing.append((row, home, away))
            continue
        if canon(m["home"]) == home:
            ph, pd, pa = m["p_home"], m["p_draw"], m["p_away"]
        else:  # stored reversed
            ph, pd, pa = m["p_away"], m["p_draw"], m["p_home"]
        # renormalize defensively
        s = ph + pd + pa
        ph, pd, pa = ph / s, pd / s, pa / s
        hg, ag, info = modal_score(ph, pd, pa)
        out.append({"row": row, "group": grp, "home": home, "away": away,
                    "hg": hg, "ag": ag, "p": [round(ph, 3), round(pd, 3), round(pa, 3)],
                    "outcome": info["outcome"], "source": m.get("source", "")})
    if missing:
        print("MISSING ODDS:", missing)
        sys.exit(1)
    (DATA / "group_predictions.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    cur = None
    for p in out:
        if p["group"] != cur:
            cur = p["group"]
            print(f"\n--- Group {cur} ---")
        print(f'r{p["row"]:>2}  {p["home"]:<24} {p["hg"]}-{p["ag"]} {p["away"]:<24} '
              f'pH/D/A={p["p"]}')
    print(f"\n{len(out)} matches predicted -> data/group_predictions.json")


if __name__ == "__main__":
    main()
