"""Regenerate paper/figs/fig_realism.{pdf,png}.

EV-optimal scoreline pick vs the realistic rounded-expected-goals readout, both
over the identical probability model, backtested on 2018+2022 (3/2/1 rule).
Data: data/backtest/realism_backtest.json (scripts/realism_backtest.py).

  Left  -- scoreline accuracy: goal error per match by year + pooled. The
           realistic readout lands closer to the actual score in both years;
           exact-score counts annotated.
  Right -- pool points by year + pooled: realistic matches the EV pick at no
           cost (EV ahead in the orderly 2018, realistic ahead in the chaotic
           2022, level pooled), so realism here is free, not paid for.

No in-image title (the paper caption carries it); panel subtitles kept.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
BT = json.loads((ROOT / "data" / "backtest" / "realism_backtest.json").read_text())
FIGS = ROOT / "paper" / "figs"

BLUE = "#1f77b4"      # EV-optimal
GREEN = "#2ca02c"     # realistic
GREY = "#9e9e9e"

per = {r["year"]: r for r in BT["per_year"]}
pooled = BT["pooled"]
years = [2018, 2022]
ev_gerr = [per[y]["ev"]["gerr"] / per[y]["n"] for y in years] + [pooled["ev"]["gerr"] / pooled["n"]]
re_gerr = [per[y]["re"]["gerr"] / per[y]["n"] for y in years] + [pooled["re"]["gerr"] / pooled["n"]]
ev_pts = [per[y]["ev"]["pts"] for y in years] + [pooled["ev"]["pts"]]
re_pts = [per[y]["re"]["pts"] for y in years] + [pooled["re"]["pts"]]
ev_exact = [per[y]["ev"]["exact"] for y in years] + [pooled["ev"]["exact"]]
re_exact = [per[y]["re"]["exact"] for y in years] + [pooled["re"]["exact"]]
labels = ["2018", "2022", "Pooled"]

fig, (axL, axR) = plt.subplots(1, 2, figsize=(13, 5))
x = np.arange(len(labels))
w = 0.38

# Left: goal error per match (lower = closer to reality)
b1 = axL.bar(x - w / 2, ev_gerr, w, color=BLUE, label="EV-optimal pick")
b2 = axL.bar(x + w / 2, re_gerr, w, color=GREEN, label="Realistic readout")
for rect, v, ex in zip(b1, ev_gerr, ev_exact):
    axL.text(rect.get_x() + rect.get_width() / 2, v + 0.02, f"{v:.2f}",
             ha="center", va="bottom", fontsize=10)
for rect, v, ex in zip(b2, re_gerr, re_exact):
    axL.text(rect.get_x() + rect.get_width() / 2, v + 0.02, f"{v:.2f}",
             ha="center", va="bottom", fontsize=10)
axL.set_xticks(x); axL.set_xticklabels(labels)
axL.set_ylabel("Goal error per match (lower is closer)")
axL.set_ylim(0, 2.5)
axL.set_title("Closer to the real score", fontsize=12, loc="left")
axL.legend(frameon=False, loc="upper right")
axL.text(2, re_gerr[2] - 0.28, f"exact: {re_exact[2]} vs {ev_exact[2]}",
         ha="center", fontsize=9, color=GREEN, fontweight="bold")
for s in ("top", "right"):
    axL.spines[s].set_visible(False)

# Right: pool points (no cost)
b3 = axR.bar(x - w / 2, ev_pts, w, color=BLUE, label="EV-optimal pick")
b4 = axR.bar(x + w / 2, re_pts, w, color=GREEN, label="Realistic readout")
for rect, v in zip(b3, ev_pts):
    axR.text(rect.get_x() + rect.get_width() / 2, v + 0.8, str(v),
             ha="center", va="bottom", fontsize=10)
for rect, v in zip(b4, re_pts):
    axR.text(rect.get_x() + rect.get_width() / 2, v + 0.8, str(v),
             ha="center", va="bottom", fontsize=10)
axR.set_xticks(x); axR.set_xticklabels(labels)
axR.set_ylabel("Pool points (backtested, 3/2/1)")
axR.set_ylim(0, max(ev_pts + re_pts) * 1.18)
axR.set_title("At no cost in pool points", fontsize=12, loc="left")
axR.legend(frameon=False, loc="upper left")
for s in ("top", "right"):
    axR.spines[s].set_visible(False)

fig.tight_layout()
fig.savefig(FIGS / "fig_realism.pdf")
fig.savefig(FIGS / "fig_realism.png", dpi=150)
print("wrote fig_realism (EV vs realistic):",
      f"goal-err pooled {ev_gerr[2]:.3f}->{re_gerr[2]:.3f}, "
      f"pts {ev_pts[2]}->{re_pts[2]}, exact {ev_exact[2]}->{re_exact[2]}")
