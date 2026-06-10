"""Regenerate paper/figs/fig_rotation.{pdf,png}.

The rotation-aware adjustment on the 30 final-matchday games of 2018 and 2022.
Reducing the Elo rating of a team that has CLINCHED qualification (eliminated
teams are not penalized -- they keep playing freely) improves the pooled
matchday-3 Brier score; the curve rises with the penalty and peaks at the search
boundary, the signature of a sample-fit effect. At a 120-point penalty the gain
is ~2.7%, rising to ~3.8% at 180.

The improvement curve is recomputed here from the backtest data via the
machinery in scripts/rotation.py (status_before_md3 / elo_hda / brier on the
matchday-3 games of data/backtest/results_{2018,2022}.json + elo_{year}.json),
penalizing clinched teams only. No in-image title (the paper caption carries it).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import rotation as R  # noqa: E402

DATA = R.DATA
BLUE = "#1f77b4"


def run_clinched(year, penalty):
    """Pooled matchday-3 Brier with a clinched-only Elo rotation penalty."""
    elo = json.loads((DATA / f"elo_{year}.json").read_text())
    res = json.loads((DATA / f"results_{year}.json").read_text())
    groups = R.GROUPS[year]
    host = R.HOSTS[year]
    team_group = {t: g for g, ts in groups.items() for t in ts}

    def look(t):
        return elo.get(t, elo.get(R.ALIAS.get(t, t)))

    def norm(t):
        return t if look(t) is not None else R.ALIAS.get(t, t)

    gm = defaultdict(list)
    for m in res:
        h, a = norm(m["home"]), norm(m["away"])
        if h in team_group and a in team_group and team_group[h] == team_group[a]:
            gm[team_group[h]].append((h, a, m["hg"], m["ag"]))

    bb = ab = 0.0
    n = 0
    for g, ms in gm.items():
        if len(ms) < 6:
            continue
        md12, md3 = ms[:4], ms[4:6]
        md3_fix = [(h, a) for h, a, _, _ in md3]
        stat = R.status_before_md3(groups[g], md12, md3_fix)
        for (h, a, hg, ag) in md3:
            ra0 = look(h) + (40 if h == host else 0)
            rb0 = look(a) + (40 if a == host else 0)
            ra = ra0 - (penalty if stat[h] == "clinched" else 0)
            rb = rb0 - (penalty if stat[a] == "clinched" else 0)
            real = R.outcome(hg, ag)
            p0 = dict(zip("HDA", R.elo_hda(ra0, rb0)))
            p1 = dict(zip("HDA", R.elo_hda(ra, rb)))
            bb += R.brier(p0, real)
            ab += R.brier(p1, real)
            n += 1
    return bb, ab, n


penalties = [0, 40, 60, 80, 100, 120, 150, 180]
improvement = []
for pen in penalties:
    BB = AB = N = 0
    for yr in (2018, 2022):
        b, a, n = run_clinched(yr, pen)
        BB += b
        AB += a
        N += n
    base = BB / N
    adj = AB / N
    improvement.append(100 * (base - adj) / base)

fig, ax = plt.subplots(figsize=(7.2, 5))
ax.axhline(0, color="0.7", linestyle="--", lw=1)
ax.plot(penalties, improvement, "-o", color=BLUE, lw=2, markersize=8)

peak_i = max(range(len(penalties)), key=lambda i: improvement[i])
px, py = penalties[peak_i], improvement[peak_i]
ax.annotate(f"peak +{py:.1f}%\nat −{px} Elo",
            xy=(px, py), xytext=(px - 55, py - 0.5), fontsize=12,
            arrowprops=dict(arrowstyle="->", color="black", lw=1.2))

ax.set_xlabel("Rotation penalty for a clinched team (Elo points)")
ax.set_ylabel("Improvement in matchday-3 prediction (%)")
ax.set_xlim(-5, 190)
ax.set_ylim(-0.2, max(improvement) + 0.5)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.tight_layout()
fig.savefig(FIGS := ROOT / "paper" / "figs" / "fig_rotation.pdf")
fig.savefig(ROOT / "paper" / "figs" / "fig_rotation.png", dpi=150)
print("wrote fig_rotation", [round(v, 2) for v in improvement])
