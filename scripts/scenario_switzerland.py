"""Switzerland title-run scenario (Uzbekistan house style): ONE simulated
tournament in which Switzerland win the World Cup (generator seed 907:
R16 Portugal, QF Argentina, SF Brazil, FINAL Spain — four giants in a row),
champion probabilities traced match by match via condition.conditional_probs.
Writes archive/Switzerland_World_Cup_scenario.{png,json}."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import condition as C
from dryrun import generate_realization, kl_bits

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "archive"
CACHE = OUT / "Switzerland_title_trajectory.json"
GEN_SEED = 907
N = 8000

g_res, ko_res, champ = generate_realization(GEN_SEED)
assert champ == "Switzerland", champ

group_order = sorted(g_res)
ko_order = list(C.R32) + list(C.R16) + list(C.QF) + list(C.SF) + [104]

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
            sui = champ_now.get("Switzerland", 0.0)
            top = max(champ_now, key=champ_now.get)
            print(f"  [{i:3}/104] {label:<16} info={bits:5.3f} | "
                  f"Switzerland {sui*100:4.1f}% | leader {top} "
                  f"{champ_now[top]*100:.0f}%", flush=True)

    CACHE.write_text(json.dumps(traj, ensure_ascii=False, indent=1))

champ0 = traj[0]["champion"]

# --------------- figure (Uzbekistan-scenario house style) ------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GROUP_END = 72
TEAL = "#11a0b8"
TEAMS = [
    ("Switzerland", TEAL, 4.5),
    ("Spain", "#cc2336", 2.2),
    ("Argentina", "#1f2440", 2.2),
    ("Brazil", "#e8a000", 2.2),
    ("Portugal", "#9a9a9a", 2.2),
]

ns = [s["n"] for s in traj]
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12.2, 9.5),
                               gridspec_kw={"height_ratios": [2.0, 1.0]})

for team, col, lw in TEAMS:
    ys = [100 * s["champion"].get(team, 0.0) for s in traj]
    ax1.plot(ns, ys, color=col, lw=lw, label=team,
             zorder=5 if team == "Switzerland" else 3,
             solid_capstyle="round")

ax1.axvspan(0, GROUP_END, color="0.96", zorder=0)
ax1.text(GROUP_END * 0.55, 95, "group stage", ha="center", color="0.6", fontsize=15)
ax1.text((GROUP_END + 104) / 2, 95, "knockouts", ha="center", color="0.6", fontsize=15)
ax1.set_ylabel("P(champion), %", fontsize=15)
ax1.set_xlim(0, 105)
ax1.set_ylim(0, 100)
ax1.tick_params(labelsize=14)
one_in = round(1 / champ0["Switzerland"])
ax1.set_title(f"The 1-in-{one_in} world: SWITZERLAND win "
              f"(simulated, seed {GEN_SEED})",
              fontsize=18, fontweight="bold", color=TEAL, loc="left", pad=12)
ax1.legend(frameon=False, loc="upper left", fontsize=15,
           bbox_to_anchor=(0.0, 0.97))
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)

ax1.annotate("flat at ~1% the\nentire tournament...",
             xy=(60, 1.6), xytext=(44, 36),
             fontsize=14, color=TEAL, ha="left",
             arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.8))
ax1.annotate("...then beats PORTUGAL, ARGENTINA,\nBRAZIL and SPAIN in the final\n"
             "— four giants = CHAMPION",
             xy=(103.6, 99), xytext=(62, 72),
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
top = max((s for s in traj if s["n"] >= 1), key=lambda s: s["info_bits"])
ax2.annotate(f"{top['info_bits']:.2f} bits — the tournament's\nmost surprising result",
             xy=(top["n"], top["info_bits"] * 0.98),
             xytext=(52, top["info_bits"] * 0.65),
             fontsize=14, color="#222", ha="left",
             arrowprops=dict(arrowstyle="->", color="#222", lw=1.4))
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)

fig.text(0.045, 0.012,
         "One simulated path of the locked pre-registered model.  "
         "Avraa's prediction model",
         fontsize=10, color="0.45")
fig.tight_layout(rect=(0, 0.025, 1, 1))
fig.savefig(OUT / "Switzerland_World_Cup_scenario.png", dpi=150)
print("wrote archive/Switzerland_World_Cup_scenario.png")
