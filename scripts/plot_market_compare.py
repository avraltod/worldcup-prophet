"""Model vs market: compare the model's conditional champion forecast with the
live prediction-market odds. With one snapshot it draws a baseline bar
comparison; with several it overlays the two probability-revision trajectories
(solid = model, dashed = market) so we can see which leads, lags, or tracks."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).parent.parent
traj = json.loads((ROOT / "data" / "trajectory.json").read_text())
FIGS = ROOT / "paper" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)

base = traj[0]["champion"]
teams = [t for t, _ in sorted(base.items(), key=lambda kv: -kv[1])[:8]]
COL = {"Spain": "#C8102E", "Argentina": "#6CACE4", "France": "#0055A4",
       "England": "#1a1a2e", "Portugal": "#006600", "Brazil": "#FFC400",
       "Germany": "#888", "Netherlands": "#FF8800"}
plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 200})

if len(traj) == 1:
    # baseline bar comparison: model vs market
    e = traj[0]
    mk = e.get("market_champion", {})
    md = e["champion"]
    y = np.arange(len(teams))[::-1]
    w = 0.38
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    ax.barh(y + w / 2, [md.get(t, 0) * 100 for t in teams], w,
            color="#0072B2", label="Model (this paper)")
    ax.barh(y - w / 2, [mk.get(t, 0) * 100 for t in teams], w,
            color="#E69F00", label="Market (Polymarket)")
    for yi, t in zip(y, teams):
        ax.text(md.get(t, 0) * 100 + 0.3, yi + w / 2, f"{md.get(t,0)*100:.0f}", va="center", fontsize=7)
        ax.text(mk.get(t, 0) * 100 + 0.3, yi - w / 2, f"{mk.get(t,0)*100:.0f}", va="center", fontsize=7)
    ax.set_yticks(y); ax.set_yticklabels(teams, fontsize=9)
    ax.set_xlabel("Champion probability, %")
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    fig.tight_layout()
    out = "fig_market_baseline"
else:
    # dual trajectories over time
    x = [e["n_played"] for e in traj]
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    for t in teams[:5]:
        ym = [e["champion"].get(t, 0) * 100 for e in traj]
        yk = [e.get("market_champion", {}).get(t, 0) * 100 for e in traj]
        ax.plot(x, ym, "-", lw=1.9, color=COL.get(t, "#888"), label=f"{t} (model)")
        ax.plot(x, yk, "--", lw=1.3, color=COL.get(t, "#888"), alpha=0.8)
    ax.set_xlabel("Matches played"); ax.set_ylabel("P(champion), %")
    ax.set_xlim(0, 104)
    ax.legend(fontsize=7.5, ncol=2, frameon=False)
    ax.set_title("Probability revision: model (solid) vs market (dashed)",
                 fontsize=10.5, loc="left")
    fig.tight_layout()
    out = "fig_market_trajectory"

fig.savefig(FIGS / f"{out}.pdf")
fig.savefig(FIGS / f"{out}.png")
print(f"wrote {out}.pdf/png ({len(traj)} snapshot(s))")
