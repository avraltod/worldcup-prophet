"""Regenerate paper/figs/fig_backtest_evolution.{pdf,png}.

Forecast evolution replayed on the 2018 and 2022 World Cups (two columns).
For each tournament:

  Top  -- the champion probability of the eventual winner (bold) and three
          reference teams, conditioned on actual results, rising from the
          pre-tournament prior to one.
  Bottom -- the information each result carried (orange group, blue knockout),
          with the single largest spike marked as the elimination of Brazil, the
          pre-tournament favorite (Belgium QF 2018, Croatia QF 2022).

In 2022 the group-stage Argentina loss to Saudi Arabia is annotated as moving
the forecast by only ~3 pp. Data: data/backtest/evolution_{2018,2022}.json
(per-snapshot {n, champion, info_bits, label, kind}); group stage = matches
1-48, knockouts thereafter. No in-image title (the paper caption carries it).
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FIGS = ROOT / "paper" / "figs"

GROUP = "#E69500"
KO = "#1f77b4"

# Champion (bold) + three reference teams per tournament, with colors, matching
# the figure's editorial selection.
PANELS = {
    "2018": {
        "title": "2018: how France (actual champion) emerged",
        "champ": "France",
        "teams": [("France", "#1f5fa8"), ("Brazil", "#f0b000"),
                  ("Belgium", "#d62728"), ("Croatia", "#222222")],
    },
    "2022": {
        "title": "2022: how Argentina (actual champion) emerged",
        "champ": "Argentina",
        "teams": [("Argentina", "#7fb3e0"), ("Brazil", "#2ca02c"),
                  ("France", "#1f5fa8"), ("Saudi Arabia", "#888888")],
    },
}
GROUP_END = 48  # 32-team WC: 48 group matches

fig, axes = plt.subplots(2, 2, figsize=(14, 8),
                         gridspec_kw={"height_ratios": [2.0, 1.0]})

for col, year in enumerate(("2018", "2022")):
    snaps = json.loads((DATA / "backtest" / f"evolution_{year}.json").read_text())
    ns = [s["n"] for s in snaps]
    cfg = PANELS[year]

    axT = axes[0][col]
    axB = axes[1][col]

    # Top: champion probability traces
    for team, col_c in cfg["teams"]:
        ys = [100 * s["champion"].get(team, 0.0) for s in snaps]
        lw = 3.0 if team == cfg["champ"] else 1.6
        axT.plot(ns, ys, color=col_c, lw=lw, label=team)
    axT.axvspan(0, GROUP_END, color="0.93", zorder=0)
    axT.text(GROUP_END / 2, 96, "group stage", ha="center", color="0.55", fontsize=10)
    axT.text((GROUP_END + max(ns)) / 2, 96, "knockouts", ha="center",
             color="0.55", fontsize=10)
    axT.set_ylabel("P(champion), %")
    axT.set_xlim(0, max(ns))
    axT.set_ylim(0, 100)
    axT.set_title(cfg["title"], fontsize=12, loc="left")
    axT.legend(ncol=2, frameon=False, loc="upper left", fontsize=9,
               bbox_to_anchor=(0.0, 0.88))   # sit below the "group stage" label
    for s in ("top", "right"):
        axT.spines[s].set_visible(False)

    # 2022: annotate Argentina-Saudi group upset
    if year == "2022":
        for s in snaps:
            lab = s.get("label", "") or ""
            if "Argentina" in lab and "Saudi" in lab:
                axT.annotate("Argentina lose to\nSaudi Arabia (−3pp,\nbarely matters)",
                             xy=(s["n"], 100 * s["champion"].get("Argentina", 0.2)),
                             xytext=(s["n"] + 4, 58), fontsize=9, color="0.5",
                             arrowprops=dict(arrowstyle="->", color="0.5", lw=1))
                break

    # Bottom: information per match
    bx = [s["n"] for s in snaps if s["n"] >= 1]
    by = [s["info_bits"] for s in snaps if s["n"] >= 1]
    bc = [GROUP if s["kind"] == "group" else KO for s in snaps if s["n"] >= 1]
    axB.bar(bx, by, width=0.9, color=bc, linewidth=0)
    axB.axvspan(0, GROUP_END, color="0.93", zorder=0)
    axB.set_xlabel("Matches played")
    axB.set_ylabel("Info (bits)")
    axB.set_xlim(0, max(ns))
    for s in ("top", "right"):
        axB.spines[s].set_visible(False)

    # annotate the Brazil-out spike (largest info)
    mx = max((s for s in snaps if s["n"] >= 1), key=lambda s: s["info_bits"])
    axB.annotate("Brazil out (QF)", xy=(mx["n"], mx["info_bits"]),
                 xytext=(mx["n"] - 30, mx["info_bits"] * 0.92), fontsize=10,
                 fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color="0.3", lw=1))

fig.tight_layout()
fig.savefig(FIGS / "fig_backtest_evolution.pdf")
fig.savefig(FIGS / "fig_backtest_evolution.png", dpi=150)
print("wrote fig_backtest_evolution")
