"""Figure for the 2022 group-stage replay: frozen-vs-learning champion trajectory
for the key teams, plus the per-game information content (KL, bits)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent.parent
traj = json.loads((ROOT / "data" / "replay_2022_trajectory.json").read_text())
fz, ln = traj["frozen"], traj["learning"]
x = list(range(len(fz)))                       # 0 = baseline, 1..48 = after game i

TEAMS = {"Brazil": "#009C3B", "Argentina": "#6CACE4", "France": "#0055A4",
         "Spain": "#C60B1E", "Netherlands": "#F36C21"}

plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 200})
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.6, 6.2),
                               gridspec_kw={"height_ratios": [2.1, 1]})

# --- top: champion-probability trajectories, frozen (dashed) vs learning (solid)
for team, c in TEAMS.items():
    ax1.plot(x, [s["champion"][team] * 100 for s in fz], "--", color=c, lw=1.1, alpha=0.7)
    ax1.plot(x, [s["champion"][team] * 100 for s in ln], "-", color=c, lw=1.8, label=team)
ax1.set_ylabel("Champion probability (%)")
ax1.set_xlim(0, len(fz) - 1)
ax1.legend(fontsize=8, frameon=False, ncol=5, loc="upper center")
ax1.text(0.5, -0.13, "solid = learning track (updates strength from performance)   ·   "
         "dashed = frozen track (conditions on results only)",
         transform=ax1.transAxes, ha="center", fontsize=7.5, color="#666")

# --- bottom: information content per game (KL vs previous, frozen track)
kl = [s["kl_from_prev"] for s in fz]
ax2.bar(x, [v * 1000 for v in kl], width=0.9, color="#888")
top = sorted(range(1, len(fz)), key=lambda i: -kl[i])[:2]
for i in top:
    ax2.annotate(f"{fz[i]['home']}\nv {fz[i]['away']}", (i, kl[i] * 1000),
                 textcoords="offset points", xytext=(0, 4), ha="center",
                 fontsize=6.5, color="#333")
ax2.set_ylabel("Information (milli-bits)")
ax2.set_xlabel("Group-stage match (chronological)")
ax2.set_xlim(0, len(fz) - 1)

fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(ROOT / "paper" / "figs" / f"fig_replay2022.{ext}")
print("wrote paper/figs/fig_replay2022.{pdf,png}")
