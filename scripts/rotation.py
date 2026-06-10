"""Rotation-aware layer: the biggest fixable information gap.

A team that has already clinched (or been eliminated from) advancement before its
final group match tends to rest starters, so its full-strength rating overstates
it. This module detects clinched/eliminated status before each matchday-3 game
and applies an Elo rotation penalty, then validates the adjustment on the 2018
and 2022 World Cups by checking whether it improves prediction of the matchday-3
results (the cluster of the model's worst misses).
"""
import json
import math
import sys
from collections import defaultdict
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from poisson_model import fit_rates, outcome_probs
from backtest_champion import GROUPS, HOSTS

DATA = Path(__file__).parent.parent / "data" / "backtest"
ALIAS = {"United States": "USA"}


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


def standings(played):
    """played: list of (home, away, hg, ag). Returns {team: (pts, gd, gf)}."""
    st = defaultdict(lambda: [0, 0, 0])
    for h, a, hg, ag in played:
        for t, f, x in ((h, hg, ag), (a, ag, hg)):
            st[t][0] += 3 if f > x else (1 if f == x else 0)
            st[t][1] += f - x
            st[t][2] += f
    return {t: tuple(v) for t, v in st.items()}


def status_before_md3(teams, md12, md3_fixtures):
    """For each team, classify clinched / eliminated / fighting before matchday 3,
    by enumerating all 3x3 outcomes of the two matchday-3 matches."""
    base = standings(md12)
    base = {t: list(base.get(t, [0, 0, 0])) for t in teams}
    top2 = {t: [False, False] for t in teams}  # [ever top2, ever not top2]
    scoreset = [(2, 0), (0, 2), (1, 1)]  # representative H / A / D
    for o1, o2 in product(scoreset, scoreset):
        sc = {t: list(base[t]) for t in teams}
        for (h, a), (hg, ag) in zip(md3_fixtures, (o1, o2)):
            for t, f, x in ((h, hg, ag), (a, ag, hg)):
                sc[t][0] += 3 if f > x else (1 if f == x else 0)
                sc[t][1] += f - x
                sc[t][2] += f
        order = sorted(teams, key=lambda t: tuple(sc[t]), reverse=True)
        adv = set(order[:2])
        for t in teams:
            if t in adv:
                top2[t][0] = True
            else:
                top2[t][1] = True
    out = {}
    for t in teams:
        ever_in, ever_out = top2[t]
        if ever_in and not ever_out:
            out[t] = "clinched"
        elif ever_out and not ever_in:
            out[t] = "eliminated"
        else:
            out[t] = "fighting"
    return out


def brier(p, real):
    return sum((p[o] - (1.0 if o == real else 0.0)) ** 2 for o in ("H", "D", "A"))


def run(year, penalty):
    elo = json.loads((DATA / f"elo_{year}.json").read_text())
    res = json.loads((DATA / f"results_{year}.json").read_text())
    groups = GROUPS[year]
    host = HOSTS[year]
    team_group = {t: g for g, ts in groups.items() for t in ts}

    def look(t):
        return elo.get(t, elo.get(ALIAS.get(t, t)))

    def norm(t):
        return t if look(t) is not None else ALIAS.get(t, t)

    # collect group matches per group, in date order
    gm = defaultdict(list)
    for m in res:
        h, a = norm(m["home"]), norm(m["away"])
        if h in team_group and a in team_group and team_group[h] == team_group[a]:
            gm[team_group[h]].append((h, a, m["hg"], m["ag"]))

    base_brier = adj_brier = 0.0
    base_hit = adj_hit = 0.0  # prob assigned to actual outcome
    n_md3 = 0
    rot_count = 0
    for g, ms in gm.items():
        if len(ms) < 6:
            continue
        md12 = ms[:4]
        md3 = ms[4:6]
        md3_fix = [(h, a) for h, a, _, _ in md3]
        teams = groups[g]
        stat = status_before_md3(teams, md12, md3_fix)
        for (h, a, hg, ag) in md3:
            ra0, rb0 = look(h) + (40 if h == host else 0), look(a) + (40 if a == host else 0)
            # rotation-adjusted ratings
            ra = ra0 - (penalty if stat[h] in ("clinched", "eliminated") else 0)
            rb = rb0 - (penalty if stat[a] in ("clinched", "eliminated") else 0)
            if stat[h] in ("clinched", "eliminated") or stat[a] in ("clinched", "eliminated"):
                rot_count += 1
            real = outcome(hg, ag)
            p0 = dict(zip("HDA", elo_hda(ra0, rb0)))
            p1 = dict(zip("HDA", elo_hda(ra, rb)))
            base_brier += brier(p0, real)
            adj_brier += brier(p1, real)
            base_hit += p0[real]
            adj_hit += p1[real]
            n_md3 += 1
    return {"n": n_md3, "rotated": rot_count,
            "base_brier": base_brier / n_md3, "adj_brier": adj_brier / n_md3,
            "base_hit": base_hit / n_md3, "adj_hit": adj_hit / n_md3}


if __name__ == "__main__":
    print("=== Rotation-aware layer: validation on matchday-3 games (2018+2022) ===\n")
    for penalty in (0, 40, 60, 80, 100, 120):
        agg = {"n": 0, "rotated": 0, "bb": 0, "ab": 0, "bh": 0, "ah": 0}
        for year in (2018, 2022):
            r = run(year, penalty)
            agg["n"] += r["n"]; agg["rotated"] += r["rotated"]
            agg["bb"] += r["base_brier"] * r["n"]; agg["ab"] += r["adj_brier"] * r["n"]
            agg["bh"] += r["base_hit"] * r["n"]; agg["ah"] += r["adj_hit"] * r["n"]
        bb, ab = agg["bb"] / agg["n"], agg["ab"] / agg["n"]
        ah = agg["ah"] / agg["n"]
        if penalty == 0:
            print(f"  baseline (no rotation): Brier {bb:.3f}, avg prob on actual result "
                  f"{agg['bh']/agg['n']*100:.1f}%  [{agg['rotated']} of {agg['n']} MD3 games have a clinched/out team]")
        else:
            print(f"  rotation penalty −{penalty} Elo: Brier {ab:.3f} "
                  f"({'+' if ab<bb else ''}{(bb-ab)/bb*100:.1f}% better), "
                  f"avg prob on actual {ah*100:.1f}%")
