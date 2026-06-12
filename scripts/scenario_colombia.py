"""One-off scenario figure (like archive/England_World_Cup_scenario.png and
paper/figs/fig_usa.png): take ONE simulated tournament in which Colombia wins
the title (generator seed 496: R16 Iran, QF Uruguay, SF Morocco, FINAL Spain)
and trace every contender's champion probability match by match by replaying
the path through condition.conditional_probs. Writes
archive/Colombia_World_Cup_scenario.{png,json}. Touches no locked files."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import condition as C
from dryrun import generate_realization, kl_bits

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "archive"
GEN_SEED = 496
N = 8000

g_res, ko_res, champ = generate_realization(GEN_SEED)
assert champ == "Colombia", champ

group_order = sorted(g_res)
ko_order = list(C.R32) + list(C.R16) + list(C.QF) + list(C.SF) + [104]

CACHE = OUT / "Colombia_scenario_trajectory.json"
if CACHE.exists():
    traj = json.loads(CACHE.read_text())
else:
    traj = []
    cum = {"group": {}, "ko": {}}
    base = C.conditional_probs(cum, N=N, seed=2026)
    champ0 = {t: d["champion"] for t, d in base.items() if d["champion"] > 0}
    traj.append({"label": "baseline", "n": 0, "info_bits": 0.0,
                 "champion": {t: round(p, 4) for t, p in champ0.items()},
                 "kind": "baseline"})
    prev = champ0

    steps = [("group", m) for m in group_order] + [("ko", m) for m in ko_order]
    for i, (kind, m) in enumerate(steps, 1):
        if kind == "group":
            cum["group"][str(m)] = g_res[m]
            label = f"group match {m}"
        else:
            cum["ko"][str(m)] = ko_res[m]
            label = f"KO match {m}"
        probs = C.conditional_probs(cum, N=N, seed=2026)
        champ_now = {t: d["champion"] for t, d in probs.items() if d["champion"] > 0}
        bits = kl_bits(champ_now, prev)
        traj.append({"label": label, "n": i, "info_bits": round(bits, 4),
                     "champion": {t: round(p, 4) for t, p in champ_now.items()},
                     "kind": kind})
        prev = champ_now
        if i % 12 == 0 or bits > 0.05:
            col = champ_now.get("Colombia", 0.0)
            top = max(champ_now, key=champ_now.get)
            print(f"  [{i:3}/104] {label:<16} info={bits:5.3f} | "
                  f"Colombia {col*100:4.1f}% | leader {top} {champ_now[top]*100:.0f}%",
                  flush=True)

    CACHE.write_text(json.dumps(traj, ensure_ascii=False, indent=1))

champ0 = traj[0]["champion"]

# --------------- figure (Uzbekistan-scenario house style) ------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GROUP_END = 72
TEAL = "#11a0b8"
TEAMS = [
    ("Colombia", TEAL, 4.5),
    ("Spain", "#cc2336", 2.2),
    ("France", "#1f2440", 2.2),
    ("Morocco", "#9a9a9a", 2.2),
    ("Brazil", "#e8a000", 2.2),
]

ns = [s["n"] for s in traj]
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12.2, 9.5),
                               gridspec_kw={"height_ratios": [2.0, 1.0]})

for team, col, lw in TEAMS:
    ys = [100 * s["champion"].get(team, 0.0) for s in traj]
    ax1.plot(ns, ys, color=col, lw=lw, label=team,
             zorder=5 if team == "Colombia" else 3,
             solid_capstyle="round")

ax1.axvspan(0, GROUP_END, color="0.96", zorder=0)
ax1.text(GROUP_END * 0.55, 95, "group stage", ha="center", color="0.6", fontsize=15)
ax1.text((GROUP_END + 104) / 2, 95, "knockouts", ha="center", color="0.6", fontsize=15)
ax1.set_ylabel("P(champion), %", fontsize=15)
ax1.set_xlim(0, 105)
ax1.set_ylim(0, 100)
ax1.tick_params(labelsize=14)
one_in = round(1 / champ0["Colombia"])
ax1.set_title(f"The 1-in-{one_in} world: COLOMBIA win (simulated, seed {GEN_SEED})",
              fontsize=18, fontweight="bold", color=TEAL, loc="left", pad=12)
ax1.legend(frameon=False, loc="upper left", fontsize=15,
           bbox_to_anchor=(0.0, 0.97))
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)

# two story annotations, Uzbekistan style
ax1.annotate("flat at ~1% the\nentire tournament...",
             xy=(60, 2.2), xytext=(44, 36),
             fontsize=14, color=TEAL, ha="left",
             arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.8))
ax1.annotate("...then beats SPAIN\nin the final = CHAMPION",
             xy=(103.6, 99), xytext=(70, 76),
             fontsize=14, fontweight="bold", color=TEAL, ha="left",
             arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.8))

bx = [s["n"] for s in traj if s["n"] >= 1]
by = [s["info_bits"] for s in traj if s["n"] >= 1]
ax2.bar(bx, by, width=0.9, color="#1f77b4", linewidth=0)
ax2.axvspan(0, GROUP_END, color="0.96", zorder=0)
ax2.set_xlabel("Matches played", fontsize=15)
ax2.set_ylabel("Info gained\n(bits)", fontsize=15)
ax2.set_xlim(0, 105)
ax2.tick_params(labelsize=14)
final_bits = traj[-1]["info_bits"]
ax2.annotate(f"{final_bits:.2f} bits — the tournament's\nmost surprising result",
             xy=(103, final_bits * 0.98), xytext=(56, final_bits * 0.78),
             fontsize=14, color="#222", ha="left",
             arrowprops=dict(arrowstyle="->", color="#222", lw=1.4))
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)

fig.tight_layout()
fig.savefig(OUT / "Colombia_World_Cup_scenario.png", dpi=150)
print("wrote archive/Colombia_World_Cup_scenario.png")
