"""One-off shareable graphic: the model's chance that Colombia beat Portugal
in group match 71 (MD3, Jun 28) — Monica's pick. Locked rates from
condition.RATES row 68 (Colombia lambda=0.90, Portugal lambda=1.75); the
raw-Elo counterfactual uses the KO draw formula with the pre-recalibration
7-point gap. Writes archive/Colombia_Portugal_chance.png."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from poisson_model import pois

OUT = Path(__file__).resolve().parent.parent / "archive"
TEAL = "#11a0b8"
RED = "#cc2336"
GRAY = "#9a9a9a"

# locked group model (odds-fitted): match 71
LH, LA = 0.90, 1.75
MAX_G = 8
pw = pd = pl = 0.0
grid = {}
for h in range(MAX_G + 1):
    for a in range(MAX_G + 1):
        p = pois(h, LH) * pois(a, LA)
        grid[(h, a)] = p
        if h > a:
            pw += p
        elif h == a:
            pd += p
        else:
            pl += p

# raw-Elo counterfactual (Portugal 1984 vs Colombia 1977, d = +7 Portugal)
d = 7
e = 1 / (1 + 10 ** (-d / 400))
pD_raw = 0.30 * math.exp(-abs(d) / 700)
pP_raw = e - pD_raw / 2
pC_raw = 1 - pP_raw - pD_raw

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(12.2, 6.8))

bars = [("COLOMBIA win", pw, TEAL), ("Draw", pd, GRAY), ("PORTUGAL win", pl, RED)]
ys = [2, 1, 0]
for (label, p, col), y in zip(bars, ys):
    ax.barh(y, p * 100, height=0.62, color=col)
    ax.text(p * 100 + 1.2, y, f"{p*100:.0f}%", va="center",
            fontsize=22, fontweight="bold", color=col)
    ax.text(-1.5, y, label, va="center", ha="right", fontsize=17,
            fontweight="bold" if label != "Draw" else "normal",
            color=col if label != "Draw" else "0.4")

ax.set_xlim(0, 78)
ax.set_ylim(-0.6, 2.8)
ax.axis("off")
ax.set_title("Can Colombia beat Portugal?  (group MD3 · Jun 28 · match 71)",
             fontsize=19, fontweight="bold", color=TEAL, loc="left", pad=16)

# the asterisk that matters: this was a coin flip before deadline day
ax.annotate(f"...but raw Elo (1984 v 1977) called it a coin flip:\n"
            f"Colombia {pC_raw*100:.0f}% before the market repriced it\n"
            f"by 140 Elo-equivalent points on deadline day",
            xy=(pw * 100 / 2, 2.33), xytext=(34, 2.05),
            fontsize=14.5, color=TEAL, va="center",
            arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.8))

# context lines, bottom
top3 = sorted(grid.items(), key=lambda kv: -kv[1])[:3]
top_str = "   ".join(f"{h}-{a} ({p*100:.0f}%)" for (h, a), p in top3)
fig.text(0.045, 0.16, f"most likely scores:  {top_str}",
         fontsize=15, color="0.35")
fig.text(0.045, 0.09,
         "our locked pick: 1-2 Portugal · the model's own risk note flags THIS match "
         "as the bracket's biggest sensitivity —",
         fontsize=15, color="0.35")
fig.text(0.045, 0.035,
         "if Colombia win, they likely top the group (94% qualified either way) "
         "and Portugal's quarter-final path collapses.",
         fontsize=15, color="0.35")

fig.tight_layout(rect=(0, 0.20, 1, 1))
fig.savefig(OUT / "Colombia_Portugal_chance.png", dpi=150)
print(f"Colombia {pw*100:.1f}%  draw {pd*100:.1f}%  Portugal {pl*100:.1f}%")
print("wrote archive/Colombia_Portugal_chance.png")
