"""Lean 2018/2022 backtest of the Frozen-2 KO re-pick method.

Question: under the pool rule (90' score 3/2/1 + 1 for the advancer, a slot
scored only if your projected pair actually meets there), does advancing the
cascade-favourite with EV-optimal 90' scorelines score more REAL points than a
naive "favourite 1-0" entry on the actual 2018/2022 knockout results?

Lean caveats (the full post-KO backtest removes these): historical scores are
AFTER-EXTRA-TIME, not 90' regulation, so the score-tier is approximate on the
few ET/penalty games; ratings are pre-tournament Elo (no post-group learned
drift); advancer is taken from bracket progression (authoritative).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ko_match_ev as kme
from learn import lambda_expected

DATA = Path(__file__).resolve().parent.parent / "data" / "backtest"

_ALIAS = {"United States": "USA"}        # results-file name -> elo-file name


def _rate(team, elo):
    return elo[_ALIAS.get(team, team)]


def _advancer(match, next_round, shootouts, year):
    """Team that advanced from `match`: the one appearing in the next round; for
    the final / 3rd-place fall back to the score, then the shootout record."""
    teams = {match["home"], match["away"]}
    if next_round:
        nxt = set()
        for m in next_round:
            nxt |= {m["home"], m["away"]}
        hit = teams & nxt
        if len(hit) == 1:
            return hit.pop()
    if match["hg"] > match["ag"]:
        return match["home"]
    if match["ag"] > match["hg"]:
        return match["away"]
    for s in shootouts:                      # draw -> penalty shootout
        if s["year"] == year and {s["team_a"], s["team_b"]} == teams:
            return s["winner"]
    return None


def _feed(slot, earlier, adv):
    """The two earlier-round matches whose advancers are slot's two teams."""
    out = []
    for em in earlier:
        if adv[id(em)] in (slot["home"], slot["away"]):
            out.append(em)
    return out


def _tier(pred, actual):
    ph, pa = pred
    ah, aa = actual
    if (ph, pa) == (ah, aa):
        return 3
    if ph - pa == ah - aa:
        return 2
    sgn = lambda x, y: (x > y) - (x < y)
    if sgn(ph, pa) == sgn(ah, aa):
        return 1
    return 0


def _entry_pick(home, away, elo, mode):
    """Predicted (home_goals, away_goals) and advancer for actual match (home,
    away). mode 'ev' = EV-optimal cascade pick; '10' = favourite 1-0 / draw 1-1."""
    fav, dog = (home, away) if _rate(home, elo) >= _rate(away, elo) else (away, home)
    lh, la = lambda_expected(_rate(fav, elo), _rate(dog, elo))   # fav home-oriented
    if mode == "ev":
        best = kme.match_ev(lh, la)
        adv = fav if best["advancer"] == "home" else dog
        fh, fa = best["score"]                              # (fav goals, dog goals)
    else:                                                   # naive favourite 1-0
        adv, (fh, fa) = fav, (1, 0)
    pred = (fh, fa) if home == fav else (fa, fh)
    return pred, adv


def backtest_year(year):
    results = json.load(open(DATA / f"results_{year}.json"))
    elo = json.load(open(DATA / f"elo_{year}.json"))
    shootouts = json.load(open(DATA / "shootouts.json"))
    ko = results[-16:]
    rounds = {"R16": ko[:8], "QF": ko[8:12], "SF": ko[12:14],
              "3RD": [ko[14]], "FINAL": [ko[15]]}
    nxt = {"R16": rounds["QF"], "QF": rounds["SF"], "SF": rounds["FINAL"],
           "3RD": [], "FINAL": []}
    adv = {id(m): _advancer(m, nxt[r], shootouts, year)
           for r, ms in rounds.items() for m in ms}
    feeds = {}                              # match -> (earlier match, earlier match)
    for slot in rounds["QF"]:
        feeds[id(slot)] = _feed(slot, rounds["R16"], adv)
    for slot in rounds["SF"]:
        feeds[id(slot)] = _feed(slot, rounds["QF"], adv)
    for slot in rounds["FINAL"]:
        feeds[id(slot)] = _feed(slot, rounds["SF"], adv)

    out = {}
    for mode in ("ev", "10"):
        my_adv, pts, exp = {}, 0.0, 0.0
        # R16 reach is 1 (fixed pairs); later slots scored only if our projected
        # pair (our advancers of the two feeding matches) equals the actual pair.
        for r in ("R16", "QF", "SF", "3RD", "FINAL"):
            for slot in rounds[r]:
                pred, padv = _entry_pick(slot["home"], slot["away"], elo, mode)
                my_adv[id(slot)] = padv
                if r in ("R16", "3RD"):
                    occurs = True           # R16 pairs are fixed (reach = 1)
                    if r == "3RD":
                        # our projected 3rd-place pair = the two SF teams we did
                        # NOT advance; occurs iff that set equals the actual pair
                        sf_losers = {s["home"] if my_adv[id(s)] == s["away"] else s["away"]
                                     for s in rounds["SF"]}
                        occurs = sf_losers == {slot["home"], slot["away"]}
                else:
                    f = feeds[id(slot)]
                    proj = {my_adv[id(f[0])], my_adv[id(f[1])]} if len(f) == 2 else set()
                    occurs = proj == {slot["home"], slot["away"]}
                if not occurs:
                    continue
                actual = (slot["hg"], slot["ag"])
                gained = _tier(pred, actual) + (1 if padv == adv[id(slot)] else 0)
                pts += gained
        out[mode] = pts
    return out, elo


def main():
    print("Lean KO re-pick backtest (pool rule: 90' 3/2/1 + advancer; "
          "scored-if-matchup-occurs)\n")
    print(f"{'Year':6} {'EV-optimal':>11} {'naive 1-0':>11} {'edge':>7}")
    tot = {"ev": 0.0, "10": 0.0}
    for year in (2018, 2022):
        res, _ = backtest_year(year)
        tot["ev"] += res["ev"]
        tot["10"] += res["10"]
        print(f"{year:<6} {res['ev']:>11.1f} {res['10']:>11.1f} "
              f"{res['ev'] - res['10']:>+7.1f}")
    print(f"{'BOTH':6} {tot['ev']:>11.1f} {tot['10']:>11.1f} "
          f"{tot['ev'] - tot['10']:>+7.1f}")


if __name__ == "__main__":
    main()
