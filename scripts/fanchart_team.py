"""General conditional fan chart for any team's champion probability.

Compute once (all teams cached), render per team:
    python3 scripts/fanchart_team.py            # compute/refresh the cache
    python3 scripts/fanchart_team.py Netherlands "#e87000" [annotation]

Same construction as fanchart_spain.py: K outer tournament realizations from
the locked model; at each checkpoint the forecast is re-computed by
conditioning on that path's first n results (frozen-strength conditioning).
Cache: archive/fanchart_paths_all.json (every team, every checkpoint).
Figure: archive/<Team>_fanchart.png."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import condition as C

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "archive"
CACHE = OUT / "fanchart_paths_all.json"

K = 100
INNER_N = 2000
CHECKPOINTS = [12, 24, 48, 72, 88, 96, 100, 102]

if not CACHE.exists():
    _argv, sys.argv = sys.argv, sys.argv[:1]  # dryrun parses argv on import
    from dryrun import generate_realization
    sys.argv = _argv
    base = C.conditional_probs({"group": {}, "ko": {}}, N=20000, seed=2026)
    p0 = {t: d["champion"] for t, d in base.items() if d["champion"] > 0}
    ko_order = list(C.R32) + list(C.R16) + list(C.QF) + list(C.SF) + [104]
    paths = []
    for k in range(1, K + 1):
        g_res, ko_res, champ = generate_realization(k)
        steps = [("group", m) for m in sorted(g_res)] + [("ko", m) for m in ko_order]
        snaps = {}
        for n in CHECKPOINTS:
            cum = {"group": {}, "ko": {}}
            for kind, m in steps[:n]:
                if kind == "group":
                    cum["group"][str(m)] = g_res[m]
                else:
                    cum["ko"][str(m)] = ko_res[m]
            probs = C.conditional_probs(cum, N=INNER_N, seed=2026)
            snaps[n] = {t: round(d["champion"], 4) for t, d in probs.items()
                        if d["champion"] > 0}
        paths.append({"champion": champ, "snaps": {str(n): s for n, s in snaps.items()}})
        if k % 10 == 0:
            print(f"  path {k}/{K} done (champion: {champ})", flush=True)
    CACHE.write_text(json.dumps(
        {"p0": p0, "checkpoints": CHECKPOINTS, "paths": paths}))
    print("cache written")

if len(sys.argv) < 2:
    sys.exit(0)

TEAM = sys.argv[1]
COLOR = sys.argv[2] if len(sys.argv) > 2 else "#b5121b"
NOTE = sys.argv[3] if len(sys.argv) > 3 else None

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

data = json.loads(CACHE.read_text())
p0 = data["p0"].get(TEAM, 0.0)
cps = [0] + [int(n) for n in data["checkpoints"]] + [104]
M = np.zeros((len(data["paths"]), len(cps)))
M[:, 0] = p0
for i, p in enumerate(data["paths"]):
    for j, n in enumerate(cps[1:-1], 1):
        M[i, j] = p["snaps"][str(n)].get(TEAM, 0.0)
    M[i, -1] = 1.0 if p["champion"] == TEAM else 0.0
M *= 100

fig, ax = plt.subplots(figsize=(12.2, 7.6))
bands = [(5, 95), (10, 90), (20, 80), (30, 70), (40, 60)]
alphas = [0.12, 0.18, 0.26, 0.36, 0.48]
for (lo, hi), al in zip(bands, alphas):
    ax.fill_between(cps, np.percentile(M, lo, axis=0),
                    np.percentile(M, hi, axis=0),
                    color=COLOR, alpha=al, linewidth=0)
ax.plot(cps, M.mean(axis=0), color=COLOR, lw=2.6, label="mean (the martingale, ~flat)")
ax.plot(cps, np.percentile(M, 50, axis=0), color=COLOR, lw=2.0, ls="--",
        label="median path")
ax.plot(cps, np.percentile(M, 95, axis=0), color=COLOR, lw=1.2, ls=":",
        label="95th percentile")

traj = json.loads((ROOT / "data" / "trajectory_v2.json").read_text())
posts = [s for s in traj if s["phase"] == "post"]
rx = [0] + [s["match"] for s in posts]
ry = [p0 * 100] + [s["champion"].get(TEAM, 0) * 100 for s in posts]
ax.plot(rx, ry, color="#111111", lw=3.0, label="realized so far",
        solid_capstyle="round", zorder=6)
ax.scatter(rx[-1:], ry[-1:], color="#111111", s=45, zorder=7)

p95_path = np.percentile(M, 95, axis=0)
ymax = 100 if p95_path[:-1].max() > 25 else max(8.0, 1.35 * p95_path[:-1].max())
ax.axvspan(0, 72, color="0.96", zorder=0)
ax.text(36, ymax * 0.93, "group stage", ha="center", color="0.6", fontsize=14)
ax.text(88, ymax * 0.93, "knockouts", ha="center", color="0.6", fontsize=14)
ax.set_xlim(0, 104)
ax.set_ylim(0, ymax)
ax.set_xlabel("Matches played", fontsize=15)
ax.set_ylabel(f"P({TEAM} champion), %", fontsize=15)
ax.tick_params(labelsize=13)
ax.set_title(f"Fan chart: {TEAM.upper()}'s title probability"
             + (f" — {NOTE}" if NOTE else ""),
             fontsize=17, fontweight="bold", color=COLOR, loc="left", pad=12)
ax.legend(frameon=False, fontsize=13, loc="upper left")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

win = (M[:, -1] == 100).mean()
off = " (their jump to 100% is off this scale)" if (win > 0 and ymax < 100) else ""
ax.annotate(f"champion in {win*100:.0f}% of 100 worlds{off}\n"
            f"baseline {p0*100:.1f}%",
            xy=(101, min(p95_path[-2], ymax * 0.96)), xytext=(46, ymax * 0.62),
            fontsize=13, fontweight="bold", color=COLOR,
            arrowprops=dict(arrowstyle="->", color=COLOR, lw=1.6))

fig.text(0.045, 0.030,
         f"Bands: 5–95 / 10–90 / 20–80 / 30–70 / 40–60 percentiles across "
         f"{len(data['paths'])} simulated paths of the locked model,",
         fontsize=9.5, color="0.45")
fig.text(0.045, 0.008,
         "forecast re-computed by conditioning at each checkpoint. Black: realized.  "
         "Avraa's prediction model",
         fontsize=9.5, color="0.45")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fname = OUT / f"{TEAM.replace(' ', '_')}_fanchart.png"
fig.savefig(fname, dpi=150)
print(f"wrote {fname.relative_to(ROOT)}")
