"""Regenerate paper/figs/fig_trajectory_demo.{pdf,png}.

Illustrative dress rehearsal of the live study on ONE simulated tournament
(not the real forecast). Two stacked panels:

  Upper -- each contender's champion probability traced match by match, from the
           pre-tournament prior on the left to the realized outcome (Spain wins)
           on the right: flat through the group stage, moving sharply once
           eliminations begin.
  Lower -- the information content of each result in bits, orange for group
           matches and blue for knockouts, near zero through the group stage and
           spiking at knockout eliminations.

Data: data/dryrun_trajectory.json (104 snapshots: {label, n, info_bits,
champion, kind}). Group stage = matches 1-72, knockouts = 73-104.
No in-image title (the paper caption carries it).
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
GROUP_END = 72  # last group match

TEAM_COLORS = {
    "Spain": "#d62728",
    "Argentina": "#7fb3e0",
    "France": "#1f5fa8",
    "Portugal": "#2ca02c",
    "England": "#222222",
    "Brazil": "#f0b000",
}

snaps = json.loads((DATA / "dryrun_trajectory.json").read_text())
ns = [s["n"] for s in snaps]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 9),
                               gridspec_kw={"height_ratios": [2.0, 1.0]})

# --- Upper: champion probability traces ---
for team, col in TEAM_COLORS.items():
    ys = [100 * s["champion"].get(team, 0.0) for s in snaps]
    ax1.plot(ns, ys, color=col, lw=2.2, label=team)

ax1.axvspan(0, GROUP_END, color="0.93", zorder=0)
ax1.text(GROUP_END / 2, 96, "group stage", ha="center", color="0.55", fontsize=11)
ax1.text((GROUP_END + max(ns)) / 2, 96, "knockouts", ha="center",
         color="0.55", fontsize=11)
ax1.set_xlabel("Matches played")
ax1.set_ylabel("P(champion), %")
ax1.set_xlim(0, max(ns))
ax1.set_ylim(0, 100)
ax1.legend(ncol=3, frameon=False, loc="upper left", fontsize=10,
           bbox_to_anchor=(0.0, 0.88))   # sit below the "group stage" label
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)

# --- Lower: information content per match ---
bx = [s["n"] for s in snaps if s["n"] >= 1]
by = [s["info_bits"] for s in snaps if s["n"] >= 1]
bc = [GROUP if s["kind"] == "group" else KO for s in snaps if s["n"] >= 1]
ax2.bar(bx, by, width=0.9, color=bc, linewidth=0)
ax2.axvspan(0, GROUP_END, color="0.93", zorder=0)
ax2.set_xlabel("Matches played")
ax2.set_ylabel("Info gained\n(bits)")
ax2.set_xlim(0, max(ns))
ax2.set_title("Information content per match (orange=group, blue=knockout)",
              fontsize=12, loc="left")
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)

fig.tight_layout()
fig.savefig(FIGS / "fig_trajectory_demo.pdf")
fig.savefig(FIGS / "fig_trajectory_demo.png", dpi=150)
print("wrote fig_trajectory_demo")
