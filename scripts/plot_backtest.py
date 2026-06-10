"""Regenerate paper/figs/fig_backtest.{pdf,png}.

Out-of-sample sanity check on the 2018 and 2022 World Cups (128 matches). Two
panels:

  Left  -- reliability of the model's top pick. For each confidence bin, the
           actual hit rate against the model's predicted probability, one line
           per tournament, dot size proportional to the number of matches in the
           bin, with the y=x perfect-calibration diagonal. Data:
           data/backtest/backtest_results.json["<year>"]["bins"] = {bin: [hits, n]};
           legend Brier skill = 1 - brier_model/brier_unif.
  Right  -- the pre-tournament probability the model and the betting market each
           assigned to the eventual champion (France 2018, Argentina 2022).
           Model from data/backtest/champion_backtest.json (actual_prob);
           market from data/backtest/market_odds.json.

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

bt = json.loads((DATA / "backtest" / "backtest_results.json").read_text())
champ = json.loads((DATA / "backtest" / "champion_backtest.json").read_text())
market = json.loads((DATA / "backtest" / "market_odds.json").read_text())

fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.5, 5.3))

# --- Left: calibration ---
axL.plot([30, 100], [30, 100], "--", color="0.6", lw=1.2,
         label="perfect calibration")
colors = {"2018": BLUE, "2022": ORANGE}
actual_team = {"2018": "France", "2022": "Argentina"}
for yr in ("2018", "2022"):
    bins = bt[yr]["bins"]
    xs, ys, ns = [], [], []
    for b in sorted(bins, key=float):
        h, n = bins[b]
        xs.append(float(b) * 100 + 5)   # bin center, e.g. 0.4 -> 45%
        ys.append(100 * h / n)
        ns.append(n)
    skill = 1 - bt[yr]["brier_model"] / bt[yr]["brier_unif"]
    axL.plot(xs, ys, "-", color=colors[yr], lw=1.5, zorder=2)
    axL.scatter(xs, ys, s=[20 + 12 * n for n in ns], color=colors[yr],
                zorder=3, label=f"{yr} (Brier skill {round(100 * skill)}%)")

axL.set_xlabel("Model's predicted probability (top pick), %")
axL.set_ylabel("Actual hit rate, %")
axL.set_xlim(30, 100)
axL.set_ylim(20, 100)
axL.set_title("Calibration: predicted vs realized (dot size = #matches)",
              fontsize=12, loc="left")
axL.legend(frameon=False, loc="upper left")
for s in ("top", "right"):
    axL.spines[s].set_visible(False)

# --- Right: champion probability, model vs market ---
years = ["2018", "2022"]
model_p = [100 * champ[y]["actual_prob"] for y in years]
mkt = {}
for y in years:
    team = actual_team[y]
    mkt[y] = next(t["champion_pct"] for t in market[y] if t["team"] == team) * 100
market_p = [mkt[y] for y in years]

x = np.arange(len(years))
w = 0.38
b1 = axR.bar(x - w / 2, model_p, w, color=BLUE, label="Model")
b2 = axR.bar(x + w / 2, market_p, w, color=ORANGE, label="Market")
for rect, v in zip(list(b1) + list(b2), model_p + market_p):
    axR.text(rect.get_x() + rect.get_width() / 2, v + 0.3, f"{round(v)}%",
             ha="center", va="bottom", fontsize=11)
axR.set_xticks(x)
axR.set_xticklabels([f"{y}\n(actual: {actual_team[y]})" for y in years])
axR.set_ylabel("Pre-tournament champion probability, %")
axR.set_ylim(0, 25)
axR.set_title("Probability assigned to the eventual champion", fontsize=12, loc="left")
axR.legend(frameon=False, loc="upper right")
for s in ("top", "right"):
    axR.spines[s].set_visible(False)

fig.tight_layout()
fig.savefig(FIGS / "fig_backtest.pdf")
fig.savefig(FIGS / "fig_backtest.png", dpi=150)
print("wrote fig_backtest")
