"""Companion to fanchart_spain.py: the FROZEN forecast's 'fan'.
A frozen forecast never updates, so its fan has zero width for 104 matches and
resolves to {0,1} all at once at the final whistle (29% of cached paths end at
1). The conditional fan's 5-95 envelope is ghosted behind for contrast: the
information is the same, conditioning just reveals it gradually.
Reads archive/Spain_fanchart_paths.json. Writes archive/Spain_fanchart_frozen.png."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "archive"
CRIMSON = "#b5121b"

data = json.loads((OUT / "Spain_fanchart_paths.json").read_text())
p0 = data["p0"] * 100
cps = [0] + [int(n) for n in data["checkpoints"]]
M = np.zeros((len(data["paths"]), len(cps)))
M[:, 0] = data["p0"]
for i, p in enumerate(data["paths"]):
    for j, n in enumerate(cps[1:], 1):
        M[i, j] = p[str(n)]
M *= 100
win_share = (M[:, -1] == 100).mean()

fig, ax = plt.subplots(figsize=(12.2, 7.6))

# ghost: the conditional fan's outer envelope
ax.fill_between(cps, np.percentile(M, 5, axis=0), np.percentile(M, 95, axis=0),
                color="0.75", alpha=0.35, linewidth=0,
                label="conditional fan (5–95), for contrast")

# the frozen 'fan': a flat line, then instant resolution
ax.plot([0, 104], [p0, p0], color=CRIMSON, lw=3.4, solid_capstyle="round",
        label="frozen forecast: flat at 27.0% for 104 matches")
ax.plot([104, 104], [p0, 100], color=CRIMSON, lw=2.0, ls=":")
ax.plot([104, 104], [p0, 0], color=CRIMSON, lw=2.0, ls=":")
ax.scatter([104], [100], s=[900 * win_share], color=CRIMSON, zorder=6)
ax.scatter([104], [0], s=[900 * (1 - win_share)], color=CRIMSON, zorder=6)
ax.annotate(f"CHAMPION\n({win_share*100:.0f}% of worlds)", xy=(104, 100),
            xytext=(88, 88), fontsize=13, fontweight="bold", color=CRIMSON,
            ha="left", arrowprops=dict(arrowstyle="->", color=CRIMSON, lw=1.5))
ax.annotate(f"not champion\n({(1-win_share)*100:.0f}% of worlds)", xy=(104, 0),
            xytext=(86, 12), fontsize=13, color=CRIMSON, ha="left",
            arrowprops=dict(arrowstyle="->", color=CRIMSON, lw=1.5))

ax.axvspan(0, 72, color="0.96", zorder=0)
ax.text(36, 93, "group stage", ha="center", color="0.6", fontsize=14)
ax.text(86, 93, "knockouts", ha="center", color="0.6", fontsize=14)
ax.set_xlim(0, 106)
ax.set_ylim(0, 100)
ax.set_xlabel("Matches played", fontsize=15)
ax.set_ylabel("P(Spain champion), %", fontsize=15)
ax.tick_params(labelsize=13)
ax.set_title("The FROZEN forecast's fan chart: no fan at all — all news arrives at once",
              fontsize=17, fontweight="bold", color=CRIMSON, loc="left", pad=12)
ax.legend(frameon=False, fontsize=13, loc="center left")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.text(0.045, 0.030,
         "A forecast that never conditions on results stays at its prior for the whole "
         "tournament and resolves to 0/1 in one step at the final.",
         fontsize=9.5, color="0.45")
fig.text(0.045, 0.008,
         "Same information, zero gradualism — the conditional fan (gray) spreads the "
         "same resolution over the knockout fortnight.  Avraa's prediction model",
         fontsize=9.5, color="0.45")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(OUT / "Spain_fanchart_frozen.png", dpi=150)
print("wrote archive/Spain_fanchart_frozen.png")
