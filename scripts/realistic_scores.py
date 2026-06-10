"""Canonical realistic scorelines for the full 104-match entry.

The readout: round the fitted expected goals (lh, la) to a scoreline, with the
predicted result preserved -- the locked winner always takes the higher score,
and a genuinely even tie stays level (decided on penalties in the knockouts).
This predicts actual scores better than the points-optimal pick: on the 128 real
matches of 2018+2022 it lands 18/128 exact (vs 16 for the EV pick) and is ~10%
closer on goals, at no pool-points cost (see scripts/backtest.py). The model --
probabilities, bracket, champion, slot emergence -- is unchanged; only the
scoreline readout differs.

Writes:
  data/predictions_realistic.json   all 104 {num, stage, home, away, hg, ag, pen, adv, ev}
  data/group_predictions.json       hg/ag updated in place (results preserved)
  data/ko_scores_321.json           {num: [hg, ag]} (realistic; name kept for compat)
  data/match_ev_all.json            {num: expected pool points the realistic pick earns}
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import GROUP_FIXTURES, canon
from poisson_model import fit_rates
from ev321 import ev_321

DATA = Path(__file__).parent.parent / "data"

# official match number per sheet row (column A of the template)
ROW_MATCH = dict(zip(range(4, 76), [
    1, 2, 25, 28, 53, 54,   3, 8, 26, 27, 51, 52,   7, 5, 30, 29, 49, 50,
    4, 6, 31, 32, 59, 60,  10, 9, 34, 33, 56, 55,  11, 12, 36, 35, 58, 57,
    16, 15, 40, 39, 64, 63, 14, 13, 37, 38, 66, 65, 17, 18, 41, 42, 61, 62,
    19, 20, 44, 43, 69, 70, 23, 24, 48, 47, 71, 72, 22, 21, 46, 45, 67, 68]))

# Knockout ties: (num, home, away, winner, host_home, host_away)
KO_TIES = [
 (73, "South Korea", "Canada", "Canada", 0, 0), (74, "Germany", "Paraguay", "Germany", 0, 0),
 (75, "Netherlands", "Morocco", "Netherlands", 0, 0), (76, "Brazil", "Japan", "Brazil", 0, 0),
 (77, "France", "Sweden", "France", 0, 0), (78, "Ecuador", "Norway", "Norway", 0, 0),
 (79, "Mexico", "Ivory Coast", "Mexico", 1, 0), (80, "England", "Algeria", "England", 0, 0),
 (81, "United States", "Bosnia and Herzegovina", "United States", 1, 0), (82, "Belgium", "Czechia", "Belgium", 0, 0),
 (83, "Colombia", "Croatia", "Croatia", 0, 0), (84, "Spain", "Austria", "Spain", 0, 0),
 (85, "Switzerland", "Iran", "Switzerland", 0, 0), (86, "Argentina", "Uruguay", "Argentina", 0, 0),
 (87, "Portugal", "Senegal", "Portugal", 0, 0), (88, "Turkey", "Egypt", "Turkey", 0, 0),
 (89, "Germany", "France", "France", 0, 0), (90, "Canada", "Netherlands", "Netherlands", 0, 0),
 (91, "Brazil", "Norway", "Brazil", 0, 0), (92, "Mexico", "England", "England", 1, 0),
 (93, "Croatia", "Spain", "Spain", 0, 0), (94, "United States", "Belgium", "Belgium", 0, 0),
 (95, "Argentina", "Turkey", "Argentina", 0, 0), (96, "Switzerland", "Portugal", "Portugal", 0, 0),
 (97, "France", "Netherlands", "France", 0, 0), (98, "Spain", "Belgium", "Spain", 0, 0),
 (99, "Brazil", "England", "England", 0, 0), (100, "Argentina", "Portugal", "Argentina", 0, 0),
 (101, "France", "Spain", "Spain", 0, 0), (102, "England", "Argentina", "Argentina", 0, 0),
 (103, "France", "England", "France", 0, 0), (104, "Spain", "Argentina", "Spain", 0, 0),
]
HOST_BONUS = {"Mexico": 40, "United States": 40, "Canada": 40}


def realistic(lh, la, result):
    """Rounded expected goals, preserving `result` in {'H','D','A'}."""
    if result == "D":
        k = round((lh + la) / 2)
        return k, k
    hg, ag = round(lh), round(la)
    if result == "H":
        if ag > hg:
            hg, ag = ag, hg
        if hg == ag:
            hg += 1
    else:
        if hg > ag:
            hg, ag = ag, hg
        if hg == ag:
            ag += 1
    return hg, ag


def ko_realistic(lh, la, winner, home):
    """Knockout: locked winner takes the higher score; even ties go to penalties."""
    lw, ll = (lh, la) if winner == home else (la, lh)
    wg, lg = round(lw), round(ll)
    pen = False
    if wg == lg:
        if lw > ll and (lw - ll) >= 0.25:
            wg += 1
        else:
            pen = True  # even tie -> level, decided on penalties
    hg, ag = (wg, lg) if winner == home else (lg, wg)
    return hg, ag, pen


def group_probs():
    by_pair = {}
    for f in ["odds_AD.json", "odds_EH.json", "odds_IL.json"]:
        for m in json.loads((DATA / f).read_text()):
            by_pair[(canon(m["home"]), canon(m["away"]))] = m
    return by_pair


def main():
    out = []
    ev_all, ko_scores = {}, {}

    # --- groups: realistic score, result preserved from the locked pick ---
    odds = group_probs()
    preds = json.loads((DATA / "group_predictions.json").read_text())
    by_row = {p["row"]: p for p in preds}
    for row, grp, home, away in GROUP_FIXTURES:
        p = by_row[row]
        m = odds.get((home, away)) or odds.get((away, home))
        if canon(m["home"]) == home:
            ph, pd, pa = m["p_home"], m["p_draw"], m["p_away"]
        else:
            ph, pd, pa = m["p_away"], m["p_draw"], m["p_home"]
        s = ph + pd + pa
        ph, pd, pa = ph / s, pd / s, pa / s
        lh, la = fit_rates(ph, pd, pa)
        result = "H" if p["hg"] > p["ag"] else ("A" if p["hg"] < p["ag"] else "D")
        hg, ag = realistic(lh, la, result)
        p["hg"], p["ag"] = hg, ag
        num = ROW_MATCH[row]
        ev_all[str(num)] = round(ev_321(hg, ag, lh, la), 4)
        out.append({"num": num, "stage": f"Group {grp}", "home": home, "away": away,
                    "hg": hg, "ag": ag, "pen": False, "adv": None})

    (DATA / "group_predictions.json").write_text(json.dumps(preds, ensure_ascii=False, indent=1))

    # --- knockouts: Elo -> probs -> realistic score, locked winner advances ---
    info = json.loads((DATA / "elo_outright_news.json").read_text())
    ELO = {t["team"]: t["elo"] for t in info["elo"]}
    ADJ = info["injury_elo_adj"]

    def rating(t, host):
        return ELO[t] + ADJ.get(t, 0) + (HOST_BONUS.get(t, 0) if host else 0)

    for num, home, away, winner, hh, ha in KO_TIES:
        ra, rb = rating(home, hh), rating(away, ha)
        dr = ra - rb
        e = 1.0 / (1.0 + 10 ** (-dr / 400.0))
        pd = 0.30 * math.exp(-abs(dr) / 700.0)
        ph = max(0.01, e - pd / 2)
        pa = max(0.01, 1.0 - ph - pd)
        s = ph + pd + pa
        ph, pd, pa = ph / s, pd / s, pa / s
        lh, la = fit_rates(ph, pd, pa)
        hg, ag, pen = ko_realistic(lh, la, winner, home)
        ko_scores[str(num)] = [hg, ag]
        ev_all[str(num)] = round(ev_321(hg, ag, lh, la), 4)
        out.append({"num": num, "stage": "KO", "home": home, "away": away,
                    "hg": hg, "ag": ag, "pen": pen, "adv": winner})

    (DATA / "ko_scores_321.json").write_text(json.dumps(ko_scores))
    (DATA / "match_ev_all.json").write_text(json.dumps(ev_all))
    out.sort(key=lambda r: r["num"])
    (DATA / "predictions_realistic.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

    gpts = sum(v for k, v in ev_all.items() if int(k) <= 72)
    kpts = sum(v for k, v in ev_all.items() if int(k) >= 73)
    pens = [r["num"] for r in out if r["pen"]]
    print(f"wrote predictions_realistic.json ({len(out)} matches)")
    print(f"group E[pts] {gpts:.1f}  knockout E[pts] {kpts:.1f}  penalties at M{pens}")


if __name__ == "__main__":
    main()
