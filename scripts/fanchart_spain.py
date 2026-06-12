"""Central-bank-style fan chart for P(Spain champion) over the tournament.

Outer loop: K full tournament realizations from the locked model
(dryrun.generate_realization). For each, the forecast P_n(Spain champion) is
re-computed at checkpoint match counts n by conditioning on that path's first
n results (condition.conditional_probs, inner N sims). Percentile bands across
the K paths give the fan; conditional probabilities are a martingale, so the
mean stays ~flat while the bands spread to the 0/1 endpoints.
Writes archive/Spain_fanchart.{png,json}."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import condition as C
from dryrun import generate_realization

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "archive"
CACHE = OUT / "Spain_fanchart_paths.json"

K = 100                   # outer tournament paths
INNER_N = 2000            # sims per conditioning call
CHECKPOINTS = [12, 24, 48, 72, 88, 96, 100, 102]   # + n=0 baseline, n=104 indicator
TEAM = "Spain"

if CACHE.exists():
    data = json.loads(CACHE.read_text())
else:
    base = C.conditional_probs({"group": {}, "ko": {}}, N=20000, seed=2026)
    p0 = base[TEAM]["champion"]
    ko_order = list(C.R32) + list(C.R16) + list(C.QF) + list(C.SF) + [104]
    paths = []
    for k in range(1, K + 1):
        g_res, ko_res, champ = generate_realization(k)
        steps = [("group", m) for m in sorted(g_res)] + [("ko", m) for m in ko_order]
        pn = {}
        for n in CHECKPOINTS:
            cum = {"group": {}, "ko": {}}
            for kind, m in steps[:n]:
                if kind == "group":
                    cum["group"][str(m)] = g_res[m]
                else:
                    cum["ko"][str(m)] = ko_res[m]
            probs = C.conditional_probs(cum, N=INNER_N, seed=2026)
            pn[n] = probs[TEAM]["champion"]
        pn[104] = 1.0 if champ == TEAM else 0.0
        paths.append(pn)
        if k % 10 == 0:
            print(f"  path {k}/{K} done (champion: {champ})", flush=True)
    data = {"p0": p0, "checkpoints": CHECKPOINTS + [104],
            "paths": [{str(n): p[n] for n in p} for p in paths]}
    CACHE.write_text(json.dumps(data))

# ------------------------------- figure -------------------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

p0 = data["p0"]
cps = [0] + [int(n) for n in data["checkpoints"]]
paths = data["paths"]
M = np.zeros((len(paths), len(cps)))
M[:, 0] = p0
for i, p in enumerate(paths):
    for j, n in enumerate(cps[1:], 1):
        M[i, j] = p[str(n)]
M *= 100

CRIMSON = "#b5121b"
fig, ax = plt.subplots(figsize=(12.2, 7.6))

bands = [(5, 95), (10, 90), (20, 80), (30, 70), (40, 60)]
alphas = [0.12, 0.18, 0.26, 0.36, 0.48]
for (lo, hi), al in zip(bands, alphas):
    ax.fill_between(cps, np.percentile(M, lo, axis=0),
                    np.percentile(M, hi, axis=0),
                    color=CRIMSON, alpha=al, linewidth=0)

med = np.percentile(M, 50, axis=0)
mean = M.mean(axis=0)
ax.plot(cps, mean, color=CRIMSON, lw=2.6, label="mean (the martingale, ~flat)")
ax.plot(cps, med, color=CRIMSON, lw=2.0, ls="--", label="median path")

# realized so far (live v2 records)
traj = json.loads((ROOT / "data" / "trajectory_v2.json").read_text())
posts = [s for s in traj if s["phase"] == "post"]
rx = [0] + [s["match"] for s in posts]
ry = [p0 * 100] + [s["champion"].get(TEAM, 0) * 100 for s in posts]
ax.plot(rx, ry, color="#111111", lw=3.0, label="realized so far",
        solid_capstyle="round", zorder=6)
ax.scatter(rx[-1:], ry[-1:], color="#111111", s=45, zorder=7)

ax.axvspan(0, 72, color="0.96", zorder=0)
ax.text(36, 93, "group stage", ha="center", color="0.6", fontsize=14)
ax.text(88, 93, "knockouts", ha="center", color="0.6", fontsize=14)
ax.set_xlim(0, 104)
ax.set_ylim(0, 100)
ax.set_xlabel("Matches played", fontsize=15)
ax.set_ylabel("P(Spain champion), %", fontsize=15)
ax.tick_params(labelsize=13)
ax.set_title("Fan chart: SPAIN's title probability — every path the tournament can take",
              fontsize=17, fontweight="bold", color=CRIMSON, loc="left", pad=12)
ax.legend(frameon=False, fontsize=13, loc="upper left")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

ax.annotate("the median favorite's path\nhits ZERO before the final —\n"
            "in most worlds Spain die somewhere",
            xy=(cps[np.argmax(med < 1)] if (med < 1).any() else 100,
                max(med[np.argmax(med < 1)] if (med < 1).any() else 1, 1)),
            xytext=(58, 38), fontsize=13, color="#7a0c12", fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#7a0c12", lw=1.6))

fig.text(0.045, 0.012,
         f"Bands: 5–95 / 10–90 / 20–80 / 30–70 / 40–60 percentiles across {len(paths)} "
         f"simulated tournament paths of the locked model, forecast re-computed by "
         f"conditioning at each checkpoint (N={INNER_N}/call). Black: realized.  "
         "Avraa's prediction model",
         fontsize=9.5, color="0.45")
fig.tight_layout(rect=(0, 0.025, 1, 1))
fig.savefig(OUT / "Spain_fanchart.png", dpi=150)
print("wrote archive/Spain_fanchart.png")
