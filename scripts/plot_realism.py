"""Regenerate paper/figs/fig_realism.{pdf,png}.

The optimal entry against a realistic, draw-producing alternative that samples
each scoreline from its fitted distribution. Two panels:

  Left  -- draws predicted on the 2026 group stage: Optimal entry (2, blue),
           Realistic sampled entry (13, orange), Reality average (19, grey).
           Optimal draws are counted from data/match_expectations.json (the EV-
           optimal picks); realistic draws from data/realistic_sheet.json (the
           sampled alternative); the real-tournament average is ~26% of 72.
  Right  -- pool points on the 2018 and 2022 backtests under the 3/2/1 rule:
           Optimal 67 vs Realistic 46 in 2018 (-21 pts), Optimal 48 vs 45 in
           2022 (-3 pts). These optimal-vs-sampling backtest totals are the
           values reported in the paper (sec on the cost of realism) and are
           pinned here as the panel's backing data.

No in-image title (the paper caption carries it); panel subtitles kept.
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

BLUE = "#1f77b4"
ORANGE = "#E69500"
GREY = "#9e9e9e"
RED = "#cc0000"

# --- Left panel data: draws predicted (of 72 group matches) ---
me = json.loads((DATA / "match_expectations.json").read_text())
optimal_draws = sum(1 for m in me if m["pick"][0] == m["pick"][1])
sheet = json.loads((DATA / "realistic_sheet.json").read_text())
realistic_draws = sum(1 for v in sheet.values() if v[0] == v[1])
reality_draws = 19   # ~26% of 72 group matches end level historically

# --- Right panel data: pool points, optimal vs sampled (paper-reported) ---
years = ["2018 World Cup", "2022 World Cup"]
opt_pts = [67, 48]
real_pts = [46, 45]

fig, (axL, axR) = plt.subplots(1, 2, figsize=(13, 5))

# Left
labels = ["Optimal\n(your entry)", "Realistic\n(sampled)", "Reality\n(avg)"]
vals = [optimal_draws, realistic_draws, reality_draws]
cols = [BLUE, ORANGE, GREY]
bars = axL.bar(labels, vals, color=cols, width=0.6)
for rect, v in zip(bars, vals):
    axL.text(rect.get_x() + rect.get_width() / 2, v + 0.3, str(v),
             ha="center", va="bottom", fontsize=12, fontweight="bold")
axL.set_ylabel("Draws predicted (of 72 group matches)")
axL.set_ylim(0, 22)
axL.set_title("Realism: draws predicted", fontsize=12, loc="left")
for s in ("top", "right"):
    axL.spines[s].set_visible(False)

# Right
x = np.arange(len(years))
w = 0.38
b1 = axR.bar(x - w / 2, opt_pts, w, color=BLUE, label="Optimal (your entry)")
b2 = axR.bar(x + w / 2, real_pts, w, color=ORANGE, label="Realistic (sampled)")
for rect, v in zip(b1, opt_pts):
    axR.text(rect.get_x() + rect.get_width() / 2, v + 0.6, str(v),
             ha="center", va="bottom", fontsize=11)
for rect, v in zip(b2, real_pts):
    axR.text(rect.get_x() + rect.get_width() / 2, v + 0.6, str(v),
             ha="center", va="bottom", fontsize=11)
# loss annotations above the optimal bar
for xi, o, r in zip(x, opt_pts, real_pts):
    axR.text(xi - w / 2, o + 4, f"{r - o} pts", ha="center", va="bottom",
             fontsize=11, fontweight="bold", color=RED)
axR.set_xticks(x)
axR.set_xticklabels(years)
axR.set_ylabel("Pool points (backtested, 3/2/1)")
axR.set_ylim(0, 78)
axR.set_title("The cost of realism", fontsize=12, loc="left")
axR.legend(frameon=False, loc="upper right")
for s in ("top", "right"):
    axR.spines[s].set_visible(False)

fig.tight_layout()
fig.savefig(FIGS / "fig_realism.pdf")
fig.savefig(FIGS / "fig_realism.png", dpi=150)
print("wrote fig_realism")
