"""Group-stage figures: 4x3 grid of stacked qualification-probability bars,
plus a 'group difficulty' ranking bar. Colorblind-safe."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

FIGS = Path(__file__).parent.parent / "paper" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)
DATA = Path(__file__).parent.parent / "data"
qual = json.loads((DATA / "group_qual.json").read_text())

# Okabe-Ito
WIN, SECOND, THIRD, OUT = "#0072B2", "#56B4E9", "#E69F00", "#D9D9D9"
plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 200})

# ---- Fig: 4x3 grid of per-group stacked qualification bars ----
fig, axes = plt.subplots(4, 3, figsize=(8.2, 9.4))
for ax, grp in zip(axes.flat, "ABCDEFGHIJKL"):
    teams = sorted(qual[grp].items(), key=lambda x: -x[1]["qual"])
    names = [t[:11] for t, _ in teams]
    p1 = [d["p1"] * 100 for _, d in teams]
    p2 = [d["p2"] * 100 for _, d in teams]
    p3 = [d["p3adv"] * 100 for _, d in teams]
    pout = [d["pout"] * 100 for _, d in teams]
    y = np.arange(len(names))[::-1]
    ax.barh(y, p1, color=WIN, label="Win group")
    ax.barh(y, p2, left=p1, color=SECOND, label="2nd")
    ax.barh(y, p3, left=np.add(p1, p2), color=THIRD, label="3rd (advance)")
    ax.barh(y, pout, left=np.add(np.add(p1, p2), p3), color=OUT, label="Out")
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=7)
    ax.set_xlim(0, 100)
    ax.set_title(f"Group {grp}", fontsize=9, fontweight="bold", loc="left")
    ax.tick_params(axis="x", labelsize=6)
    for _, d in teams:
        pass
    # annotate qualification % at bar end
    for yi, (_, d) in zip(y, teams):
        ax.text(101, yi, f"{d['qual']*100:.0f}", va="center", fontsize=6, color="#555")
handles, labels = axes.flat[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8,
           frameon=False, bbox_to_anchor=(0.5, -0.01))
fig.tight_layout(rect=[0, 0.02, 1, 1])
fig.savefig(FIGS / "fig_group_qual.pdf", bbox_inches="tight")
fig.savefig(FIGS / "fig_group_qual.png", bbox_inches="tight")
plt.close(fig)

# ---- Fig: group difficulty (competitiveness) ranking ----
# difficulty = how contested: 100 - (top team's qual - 4th team's qual spread proxy)
# Use entropy-like measure: sum of |qual - 50| inverted, or simpler: the gap
# between the 2nd and 3rd most-likely-to-qualify team (smaller gap = tighter).
diff = []
for grp in "ABCDEFGHIJKL":
    qs = sorted((d["qual"] for d in qual[grp].values()), reverse=True)
    # competitiveness: how close the 2nd/3rd qualifiers are (the bubble fight)
    tightness = 100 * (1 - abs(qs[1] - qs[2]))  # close 2nd vs 3rd -> high
    diff.append((grp, tightness, qs))
diff.sort(key=lambda x: -x[1])
fig, ax = plt.subplots(figsize=(6.2, 3.4))
labels = [f"Group {g}" for g, _, _ in diff]
vals = [t for _, t, _ in diff]
colors = [WIN if t >= 90 else (SECOND if t >= 80 else OUT) for _, t, _ in diff]
bars = ax.barh(range(len(labels))[::-1], vals, color=colors)
ax.set_yticks(range(len(labels))[::-1])
ax.set_yticklabels(labels, fontsize=8)
ax.set_xlabel("Competitiveness index (higher = tighter race for qualification)")
ax.set_xlim(0, 100)
for b, (g, t, _) in zip(bars, diff):
    ax.text(t - 2, b.get_y() + b.get_height() / 2, f"{t:.0f}", va="center",
            ha="right", color="white", fontsize=7, fontweight="bold")
fig.tight_layout()
fig.savefig(FIGS / "fig_group_difficulty.pdf")
fig.savefig(FIGS / "fig_group_difficulty.png")
plt.close(fig)

print("wrote fig_group_qual.pdf and fig_group_difficulty.pdf")
print("Most competitive:", ", ".join(f"{g}({t:.0f})" for g, t, _ in diff[:3]))
print("Least competitive:", ", ".join(f"{g}({t:.0f})" for g, t, _ in diff[-3:]))
