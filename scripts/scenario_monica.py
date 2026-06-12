"""Monica's world: replay the group stage with every match landing exactly on
our locked picks (data/group_predictions_v2.json), EXCEPT match 71 — Colombia
beat Portugal 1-0 instead of losing 1-2. Trace Colombia's and Portugal's
conditional forecast (champion + reach-QF) after each of the 72 matches via
condition.conditional_probs. Writes archive/Monica_scenario.{png,json}."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import condition as C

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "archive"
CACHE = OUT / "Monica_scenario_trajectory.json"
N = 8000
FLIP_MATCH = 71          # Colombia - Portugal, group MD3, Jun 28
FLIP_SCORE = [1, 0]      # Monica's world (locked pick was 1-2)

picks = json.loads((ROOT / "data" / "group_predictions_v2.json").read_text())
results = {}
for r in picks:
    m = C.ROW_MATCH[r["row"]]
    results[m] = [r["hg"], r["ag"]]
results[FLIP_MATCH] = FLIP_SCORE

TRACK = ["Colombia", "Portugal", "Spain"]

if CACHE.exists():
    traj = json.loads(CACHE.read_text())
else:
    traj = []
    cum = {"group": {}, "ko": {}}
    probs = C.conditional_probs(cum, N=N, seed=2026)
    traj.append({"n": 0, "label": "baseline",
                 "teams": {t: probs[t] for t in TRACK}})
    for i, m in enumerate(sorted(results), 1):
        cum["group"][str(m)] = results[m]
        probs = C.conditional_probs(cum, N=N, seed=2026)
        traj.append({"n": i, "label": f"match {m}",
                     "teams": {t: probs[t] for t in TRACK}})
        if i % 12 == 0 or m == FLIP_MATCH:
            col, por = probs["Colombia"], probs["Portugal"]
            print(f"  [{i:2}/72] after match {m:2} | "
                  f"COL champ {col['champion']*100:4.1f}% QF {col['QF']*100:4.1f}% | "
                  f"POR champ {por['champion']*100:4.1f}% QF {por['QF']*100:4.1f}%",
                  flush=True)
    CACHE.write_text(json.dumps(traj, ensure_ascii=False, indent=1))

# --------------- figure (scenario house style) ------------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TEAL = "#11a0b8"
RED = "#cc2336"
GRAY = "#b0b0b0"

ns = [s["n"] for s in traj]
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12.2, 9.5), sharex=True)

panels = [(ax1, "QF", "P(reach quarter-final), %"),
          (ax2, "champion", "P(champion), %")]
for ax, key, ylab in panels:
    for team, col, lw in [("Colombia", TEAL, 4.0), ("Portugal", RED, 2.6),
                          ("Spain", GRAY, 1.8)]:
        ys = [100 * s["teams"][team][key] for s in traj]
        ax.plot(ns, ys, color=col, lw=lw, label=team,
                zorder=5 if team == "Colombia" else 3,
                solid_capstyle="round")
    ax.axvline(71, color="0.8", lw=1, ls="--", zorder=1)
    ax.set_ylabel(ylab, fontsize=15)
    ax.set_xlim(0, 72.5)
    ax.tick_params(labelsize=14)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)

ax1.set_title("Monica's world: 71 matches go exactly as we predicted... "
              "except hers",
              fontsize=18, fontweight="bold", color=TEAL, loc="left", pad=12)
ax1.legend(frameon=False, loc="upper left", fontsize=15)
ax2.set_xlabel("Group-stage matches played (in match order)", fontsize=15)

q_col = [100 * s["teams"]["Colombia"]["QF"] for s in traj]
q_por = [100 * s["teams"]["Portugal"]["QF"] for s in traj]
ax1.annotate(f"Jun 28, match 71:\nCOLOMBIA 1-0 Portugal\n"
             f"QF chance jumps {q_col[70]:.0f}% → {q_col[71]:.0f}%",
             xy=(71, q_col[71]), xytext=(42, 38),
             fontsize=14, fontweight="bold", color=TEAL, ha="left",
             arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.8))
ax1.annotate(f"Portugal slide\n{q_por[70]:.0f}% → {q_por[71]:.0f}%",
             xy=(71, q_por[71]), xytext=(59, 13),
             fontsize=14, fontweight="bold", color=RED, ha="left",
             arrowprops=dict(arrowstyle="->", color=RED, lw=1.8))

c_col = [100 * s["teams"]["Colombia"]["champion"] for s in traj]
c_por = [100 * s["teams"]["Portugal"]["champion"] for s in traj]
ax2.annotate(f"Colombia {c_col[70]:.1f}% → {c_col[71]:.1f}%\n"
             f"Portugal {c_por[70]:.1f}% → {c_por[71]:.1f}%",
             xy=(71, max(c_col[71], c_por[71])), xytext=(48, 16),
             fontsize=14, fontweight="bold", color="#333", ha="left",
             arrowprops=dict(arrowstyle="->", color="#333", lw=1.6))

fig.text(0.045, 0.012,
         "Locked model, conditioned match by match: all 72 group results set to our locked "
         "picks except match 71 (pick was 1-2). Spain for scale.  Avraa's prediction model",
         fontsize=10, color="0.45")
fig.tight_layout(rect=(0, 0.025, 1, 1))
fig.savefig(OUT / "Monica_scenario.png", dpi=150)
print("wrote archive/Monica_scenario.png")
