"""Regenerate paper/figs/fig_pickvalue.{pdf,png}.

Expected points per pick for all 104 predictions, sorted descending, under the
pool's three-tier (3/2/1) rule. Group picks orange, knockout picks blue.
Confident picks against weak teams sit highest, the most even games lowest; the
mean is ~0.99 points per game, and knockout values are conditional on the
predicted matchup occurring. Data: data/match_ev_all.json (104 match -> EV),
matches 1-72 group, 73-104 knockout. No in-image title.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FIGS = ROOT / "paper" / "figs"

GROUP = "#E69500"   # orange
KO = "#1f77b4"      # blue

ev = json.loads((DATA / "match_ev_all.json").read_text())
picks = [(int(m), v, "group" if int(m) <= 72 else "knockout") for m, v in ev.items()]
picks.sort(key=lambda t: -t[1])

vals = [p[1] for p in picks]
colors = [GROUP if p[2] == "group" else KO for p in picks]
mean = float(np.mean(vals))

fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(range(len(vals)), vals, width=1.0, color=colors, linewidth=0)

ax.axhline(mean, color="0.6", linestyle="--", linewidth=1.2)
ax.text(len(vals) * 0.62, mean + 0.02, f"mean {mean:.2f} pts/game",
        color="0.5", fontsize=11)

ax.set_xlabel("Match (sorted by expected points)")
ax.set_ylabel("Expected points (3/2/1 rule)")
ax.set_xlim(-1, len(vals))
ax.set_ylim(0, 1.45)

handles = [plt.Rectangle((0, 0), 1, 1, color=GROUP),
           plt.Rectangle((0, 0), 1, 1, color=KO)]
ax.legend(handles, ["group", "knockout"], frameon=False, loc="upper right")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.tight_layout()
fig.savefig(FIGS / "fig_pickvalue.pdf")
fig.savefig(FIGS / "fig_pickvalue.png", dpi=150)
print("wrote fig_pickvalue")
