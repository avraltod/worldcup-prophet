"""Opening-day shareable: two panels in the scenario-figure house style.
(A) the starting grid — locked champion probabilities, four teams cover 69%;
(B) when the answer arrives — per-match information (bits) from the full
dress rehearsal (one simulated tournament replayed through the live
conditioning pipeline), with the cumulative share overlaid: the 72 group
games carry 19% of the information, the knockouts 81%.
Writes archive/Opening_day_information.png."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "archive"
TEAL = "#11a0b8"
RED = "#cc2336"
NAVY = "#1f2440"
ORANGE = "#E69500"
BLUE = "#1f77b4"
GROUP_END = 72

traj = json.loads((ROOT / "data" / "dryrun_trajectory.json").read_text())
base = traj[0]["champion"]
infos = [(s["n"], s["info_bits"], s["kind"]) for s in traj if s["n"] >= 1]
total = sum(b for _, b, _ in infos)
group_share = sum(b for _, b, k in infos if k == "group") / total

fig, (axA, axB) = plt.subplots(2, 1, figsize=(12.2, 10.2),
                               gridspec_kw={"height_ratios": [1.15, 1.0]})

# ---------------- Panel A: the starting grid ------------------------------
top = sorted(base.items(), key=lambda kv: -kv[1])
show = top[:8]
rest = 1 - sum(p for _, p in show)
rows = [(t, p) for t, p in show] + [("the other 34 teams", rest)]
ys = range(len(rows) - 1, -1, -1)
for (team, p), y in zip(rows, ys):
    col = RED if team == "Spain" else ("0.75" if team.startswith("the other") else NAVY)
    axA.barh(y, p * 100, height=0.62, color=col)
    axA.text(p * 100 + 0.6, y, f"{p*100:.0f}%", va="center", fontsize=15,
             fontweight="bold", color=col)
    axA.text(-0.8, y, team, va="center", ha="right", fontsize=14,
             color=col, fontweight="bold" if team == "Spain" else "normal")

axA.set_xlim(0, 34)
axA.set_ylim(-0.7, len(rows) - 0.1)
axA.axis("off")
axA.set_title("Kickoff today — the locked starting grid",
              fontsize=18, fontweight="bold", color=TEAL, loc="left", pad=10)
axA.annotate("four teams already hold 69%\nof the title probability —\nthe draw "
             "and the markets did\nmost of the work before\na ball was kicked",
             xy=(10.2, 5.5), xytext=(16, 4.6),
             fontsize=14, color=NAVY, va="center",
             arrowprops=dict(arrowstyle="->", color=NAVY, lw=1.6))

# ---------------- Panel B: when the answer arrives -------------------------
ns = [n for n, _, _ in infos]
bs = [b for _, b, _ in infos]
cols = [ORANGE if k == "group" else BLUE for _, _, k in infos]
axB.bar(ns, bs, width=0.9, color=cols, linewidth=0)
axB.axvspan(0, GROUP_END, color="0.96", zorder=0)
axB.set_xlim(0, 105)
axB.set_xlabel("Matches played", fontsize=15)
axB.set_ylabel("Information per match (bits)", fontsize=15)
axB.tick_params(labelsize=14)
axB.set_title("...but when do we actually LEARN who wins?",
              fontsize=18, fontweight="bold", color=TEAL, loc="left", pad=10)
for s in ("top", "right"):
    axB.spines[s].set_visible(False)

axB.text(GROUP_END / 2, max(bs) * 0.86,
         f"all 72 group games together:\nonly {group_share*100:.0f}% of the information",
         ha="center", fontsize=15, color=ORANGE, fontweight="bold")
axB.annotate(f"the knockouts: {100*(1-group_share):.0f}%\n(the 10 biggest matches\n"
             "alone carry 69%)",
             xy=(95.8, max(bs) * 0.92), xytext=(62, max(bs) * 0.55),
             fontsize=15, fontweight="bold", color=BLUE, ha="left",
             arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.8,
                             shrinkB=4))

fig.text(0.045, 0.030,
         "Locked pre-registered forecast (June 10). Lower panel: one full simulated tournament "
         "replayed through the live pipeline, forecast re-computed",
         fontsize=10, color="0.45")
fig.text(0.045, 0.008,
         "after each of the 104 matches; information = KL divergence between consecutive "
         "champion distributions.  Avraa's prediction model",
         fontsize=10, color="0.45")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(OUT / "Opening_day_information.png", dpi=150)
print("wrote archive/Opening_day_information.png")
