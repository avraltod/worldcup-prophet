"""Publication figures for the WC2026 paper (colorblind-safe, APA-ish)."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from poisson_model import fit_rates, pois

FIGS = Path(__file__).parent.parent / "paper" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)

# Okabe-Ito colorblind-safe palette
BLUE, ORANGE, GREEN, GREY = "#0072B2", "#E69F00", "#009E73", "#999999"
plt.rcParams.update({"font.size": 9.5, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 200})

# ---- Fig 1: champion probability distribution (200k sims) -------------------
teams = ["Spain", "Argentina", "France", "England", "Portugal", "Colombia",
         "Brazil", "Netherlands", "Germany", "Ecuador", "Norway", "Croatia"]
champ = [27.4, 18.6, 14.8, 7.3, 4.2, 4.1, 3.6, 2.7, 2.2, 1.9, 1.8, 1.7]
rest = 100 - sum(champ)
fig, ax = plt.subplots(figsize=(6.4, 3.2))
colors = [BLUE] + [GREY] * (len(teams) - 1)
colors[4] = ORANGE  # Portugal highlighted for the discussion
bars = ax.bar(teams + ["36 others"], champ + [rest], color=colors + ["#cccccc"])
for b, v in zip(bars, champ + [rest]):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.4, f"{v:.1f}",
            ha="center", fontsize=8)
ax.set_ylabel("P(champion), %")
ax.set_ylim(0, 31)
plt.xticks(rotation=38, ha="right")
fig.tight_layout()
fig.savefig(FIGS / "fig1_champion_dist.pdf")
plt.close(fig)

# ---- Fig 2: head-to-head vs slot emergence (the revised picks) --------------
matches = ["M78\nEcuador vs Norway", "M83\nPortugal vs Croatia",
           "M94\nTurkey vs Belgium"]
h2h_orig = [52.6, 59.1, 55.7]      # P(original pick advances | matchup occurs), Elo
slot_orig = [20.5, 25.1, 14.3]     # slot emergence, original pick
slot_new = [24.5, 27.5, 23.9]      # slot emergence, revised pick
x = np.arange(3)
w = 0.27
fig, ax = plt.subplots(figsize=(6.0, 3.0))
ax.bar(x - w, h2h_orig, w, label="Head-to-head: original pick wins\n(if the matchup happens)", color=GREY)
ax.bar(x, slot_orig, w, label="Slot emergence: original pick", color=ORANGE)
ax.bar(x + w, slot_new, w, label="Slot emergence: revised pick", color=BLUE)
for xi, vals in zip(x, zip(h2h_orig, slot_orig, slot_new)):
    for dx, v in zip((-w, 0, w), vals):
        ax.text(xi + dx, v + 0.8, f"{v:.0f}", ha="center", fontsize=8)
ax.set_xticks(x, matches)
ax.set_ylabel("Probability, %")
ax.set_ylim(0, 88)
ax.legend(fontsize=7.5, loc="upper right", frameon=False, borderaxespad=0.1)
fig.tight_layout()
fig.savefig(FIGS / "fig2_slot_vs_h2h.pdf")
plt.close(fig)

# ---- Fig 3: scoreline distribution for the predicted final ------------------
lh, la = fit_rates(0.427, 0.281, 0.293)
G = 5
M = np.array([[pois(i, lh) * pois(j, la) for j in range(G + 1)] for i in range(G + 1)])
fig, ax = plt.subplots(figsize=(4.6, 3.9))
im = ax.imshow(M * 100, cmap="Blues", origin="lower")
for i in range(G + 1):
    for j in range(G + 1):
        v = M[i, j] * 100
        if v >= 0.45:
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=8,
                    color="white" if v > 7 else "#1a1a2e")
ax.set_xlabel("Argentina goals")
ax.set_ylabel("Spain goals")
ax.set_xticks(range(G + 1))
ax.set_yticks(range(G + 1))
# highlight the realistic pick 2-1 (Spain 2, Argentina 1)
ax.add_patch(plt.Rectangle((1 - 0.5, 2 - 0.5), 1, 1, fill=False, edgecolor=ORANGE, lw=2.2))
cb = fig.colorbar(im, ax=ax, shrink=0.85)
cb.set_label("P(scoreline), %")
fig.tight_layout()
fig.savefig(FIGS / "fig3_final_scorelines.pdf")
plt.close(fig)

print(f"figures written to {FIGS}; final fit lh={lh}, la={la}, "
      f"realistic 2-1 p={M[2,1]*100:.1f}%")
