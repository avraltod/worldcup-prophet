"""Regenerate paper/figs/fig_pivotality.{pdf,png}.

Pivotality of each match along the predicted path: the expected movement of the
champion forecast from a single result, before it is played. Group matches
(orange) average ~0.014 bits; knockout matches (blue) average ~0.11 bits; the
final reaches ~0.99 bits. Data: data/pivotality.json (list of {match, stage,
pivotality}). No in-image title (the paper caption carries it).
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FIGS = ROOT / "paper" / "figs"

GROUP = "#E69500"   # orange
KO = "#1f77b4"      # blue

rows = json.loads((DATA / "pivotality.json").read_text())
xs = [r["match"] for r in rows]
ys = [r["pivotality"] for r in rows]
colors = [GROUP if r["stage"] == "group" else KO for r in rows]

fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(xs, ys, width=0.9, color=colors, linewidth=0)

# Shade the group stage (matches 1-72)
ax.axvspan(0, 72.5, color="0.93", zorder=0)
ax.text(36, 0.93, "GROUP STAGE\n(72 matches, nearly flat)",
        ha="center", va="top", color="0.5", fontsize=11)
ax.text(88, 0.93, "KNOCKOUTS", ha="center", va="top", color="0.5", fontsize=11)

# Annotate the final and semi-finals
final = max(rows, key=lambda r: r["pivotality"])
fx, fy = final["match"], final["pivotality"]
ax.annotate("the FINAL\n0.99 bits", xy=(fx, fy), xytext=(fx - 18, 0.62),
            fontsize=12, fontweight="bold", color=KO,
            arrowprops=dict(arrowstyle="->", color=KO, lw=1.5))
# semi-finals: the two ~0.5 bars just before the final
semis = sorted([r for r in rows if r["stage"] != "group" and r["match"] < fx],
               key=lambda r: -r["pivotality"])[:2]
if semis:
    sx = semis[0]["match"]; sy = semis[0]["pivotality"]
    ax.annotate("semi-finals", xy=(sx, sy), xytext=(sx - 24, 0.43),
                fontsize=11, color=KO,
                arrowprops=dict(arrowstyle="->", color=KO, lw=1.5))

ax.set_xlabel("Match (in tournament order)")
ax.set_ylabel("Pivotality: expected forecast swing (bits)")
ax.set_xlim(0, max(xs) + 2)
ax.set_ylim(0, 1.05)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.tight_layout()
fig.savefig(FIGS / "fig_pivotality.pdf")
fig.savefig(FIGS / "fig_pivotality.png", dpi=150)
print("wrote fig_pivotality")
