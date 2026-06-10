"""Plot the forecast as it evolves: champion-probability trajectories and the
information content of each update. Reads data/trajectory.json; safe to run at
any point during the tournament (draws whatever snapshots exist so far)."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent.parent
traj = json.loads((ROOT / "data" / "trajectory.json").read_text())
FIGS = ROOT / "paper" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)

x = [e["n_played"] for e in traj]
# teams to track: top 6 from the baseline
base = traj[0]["champion"]
teams = [t for t, _ in sorted(base.items(), key=lambda kv: -kv[1])[:6]]
COLORS = {"Spain": "#C8102E", "Argentina": "#6CACE4", "France": "#0055A4",
          "England": "#1a1a2e", "Portugal": "#006600", "Brazil": "#FFDF00"}
plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 200})

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.2, 6.2),
                               gridspec_kw={"height_ratios": [3, 1.4]})
for t in teams:
    ys = [e["champion"].get(t, 0) * 100 for e in traj]
    ax1.plot(x, ys, marker="o", ms=3, lw=1.8,
             color=COLORS.get(t, "#888"), label=t)
ax1.set_ylabel("P(champion), %")
ax1.set_xlabel("Matches played")
ax1.set_xlim(0, 104)
ax1.legend(fontsize=8, ncol=3, frameon=False, loc="upper left")
ax1.set_title("Forecast evolution: champion probability after each match",
              fontsize=10.5, loc="left")

# information content per update (bits)
xb = [e["n_played"] for e in traj[1:]]
yb = [e["info_bits"] for e in traj[1:]]
ax2.bar(xb, yb, width=1.4, color="#E69F00")
ax2.set_ylabel("Info gained\n(bits)")
ax2.set_xlabel("Matches played")
ax2.set_xlim(0, 104)
ax2.set_title("Information content of each update (KL divergence)",
              fontsize=9.5, loc="left")

fig.tight_layout()
fig.savefig(FIGS / "fig_trajectory.pdf")
fig.savefig(FIGS / "fig_trajectory.png")
print(f"plotted {len(traj)} snapshots -> fig_trajectory.pdf/png")
if len(traj) > 1:
    big = max(traj[1:], key=lambda e: e["info_bits"])
    print(f"most informative update so far: '{big['label']}' "
          f"({big['info_bits']:.3f} bits)")
