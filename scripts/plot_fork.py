"""Regenerate paper/figs/fig_fork.{pdf,png}.

"One match, two futures." Champion probabilities before the predicted
Spain--France semi-final (grey) and under each result (Spain win = red,
France win = blue), for the four teams the result moves. Spain go 38 -> 61
if they win and to 0 if they lose; the result also shifts Argentina and England
because it changes their projected final opponent.

The twelve plotted percentages are the conditional-champion-distribution values
reported in the paper (sec:pivotality / sec:fork) -- the output of the
conditional re-simulation at the Spain--France semi-final node
(scripts/condition.py machinery). They are stable across seeds to within Monte
Carlo error (~0.4 pp on the champion's probability) and are pinned here as the
figure's backing data so the figure regenerates deterministically.
No in-image title (the paper caption carries it).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "paper" / "figs"

GREY = "#9e9e9e"
RED = "#cc0000"      # Spain win
BLUE = "#1f5fa8"     # France win

teams = ["Spain", "France", "Argentina", "England"]
before = [38, 20, 30, 13]      # grey: before the semi-final
spain_win = [61, 0, 27, 11]    # red:  if Spain win the semi
france_win = [0, 51, 34, 15]   # blue: if France win the semi

x = np.arange(len(teams))
w = 0.26

fig, ax = plt.subplots(figsize=(10, 5.2))
b0 = ax.bar(x - w, before, w, color=GREY, label="Before the semi-final")
b1 = ax.bar(x, spain_win, w, color=RED, label="If Spain win the semi")
b2 = ax.bar(x + w, france_win, w, color=BLUE, label="If France win the semi")

for bars, vals, col in ((b0, before, "0.35"), (b1, spain_win, RED), (b2, france_win, BLUE)):
    for rect, v in zip(bars, vals):
        ax.text(rect.get_x() + rect.get_width() / 2, v + 0.7, str(v),
                ha="center", va="bottom", fontsize=10, color=col)

ax.set_xticks(x)
ax.set_xticklabels(teams)
ax.set_ylabel("Champion probability, %")
ax.set_ylim(0, 66)
ax.legend(frameon=False, loc="upper right")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.tight_layout()
fig.savefig(FIGS / "fig_fork.pdf")
fig.savefig(FIGS / "fig_fork.png", dpi=150)
print("wrote fig_fork")
