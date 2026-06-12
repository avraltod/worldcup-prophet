"""Turkey's world (same design as scenario_monica.py): replay the group stage
with every match landing exactly on our locked picks
(data/group_predictions_v2.json), EXCEPT match 59 — Turkey beat the USA 1-0
instead of the picked 0-1. This is the head-to-head the model priced at a
literal 36.3/36.3 tie, broken toward the USA only for bracket routing.
Writes archive/Turkey_scenario.{png,json}."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import condition as C

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "archive"
CACHE = OUT / "Turkey_scenario_trajectory.json"
N = 8000
FLIP_MATCH = 59          # Turkey - United States, group D MD3, Jun 26
FLIP_SCORE = [1, 0]      # Turkey's world (v2 pick was 0-1)

picks = json.loads((ROOT / "data" / "group_predictions_v2.json").read_text())
results = {}
for r in picks:
    m = C.ROW_MATCH[r["row"]]
    results[m] = [r["hg"], r["ag"]]
results[FLIP_MATCH] = FLIP_SCORE

TRACK = ["Turkey", "United States", "Spain"]

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
            tur, usa = probs["Turkey"], probs["United States"]
            print(f"  [{i:2}/72] after match {m:2} | "
                  f"TUR champ {tur['champion']*100:4.1f}% QF {tur['QF']*100:4.1f}% | "
                  f"USA champ {usa['champion']*100:4.1f}% QF {usa['QF']*100:4.1f}%",
                  flush=True)
    CACHE.write_text(json.dumps(traj, ensure_ascii=False, indent=1))

# --------------- figure (scenario house style) ------------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TEAL = "#11a0b8"
NAVY = "#1f2440"
GRAY = "#b0b0b0"

ns = [s["n"] for s in traj]
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12.2, 9.5), sharex=True)

panels = [(ax1, "QF", "P(reach quarter-final), %"),
          (ax2, "champion", "P(champion), %")]
for ax, key, ylab in panels:
    for team, col, lw, lab in [("Turkey", TEAL, 4.0, "Turkey"),
                               ("United States", NAVY, 2.6, "USA (host)"),
                               ("Spain", GRAY, 1.8, "Spain")]:
        ys = [100 * s["teams"][team][key] for s in traj]
        ax.plot(ns, ys, color=col, lw=lw, label=lab,
                zorder=5 if team == "Turkey" else 3,
                solid_capstyle="round")
    ax.axvline(FLIP_MATCH, color="0.8", lw=1, ls="--", zorder=1)
    ax.set_ylabel(ylab, fontsize=15)
    ax.set_xlim(0, 72.5)
    ax.tick_params(labelsize=14)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)

ax1.set_title("The tightest call in the draw: what if TURKEY beat the USA? "
              "(36.3% v 36.3%)",
              fontsize=18, fontweight="bold", color=TEAL, loc="left", pad=12)
ax1.legend(frameon=False, loc="upper left", fontsize=15)
ax2.set_xlabel("Group-stage matches played (in match order)", fontsize=15)

f = FLIP_MATCH
q_tur = [100 * s["teams"]["Turkey"]["QF"] for s in traj]
q_usa = [100 * s["teams"]["United States"]["QF"] for s in traj]
ax1.annotate(f"Jun 26, match 59:\nTURKEY 1-0 USA\n"
             f"QF chance {q_tur[f-1]:.0f}% → {q_tur[f]:.0f}%",
             xy=(f, q_tur[f]), xytext=(33, 42),
             fontsize=14, fontweight="bold", color=TEAL, ha="left",
             arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.8))
ax1.annotate(f"USA slide\n{q_usa[f-1]:.0f}% → {q_usa[f]:.0f}%",
             xy=(f, q_usa[f]), xytext=(62, 17),
             fontsize=14, fontweight="bold", color=NAVY, ha="left",
             arrowprops=dict(arrowstyle="->", color=NAVY, lw=1.8))

c_tur = [100 * s["teams"]["Turkey"]["champion"] for s in traj]
c_usa = [100 * s["teams"]["United States"]["champion"] for s in traj]
ax2.annotate(f"Turkey {c_tur[f-1]:.1f}% → {c_tur[f]:.1f}%\n"
             f"USA {c_usa[f-1]:.1f}% → {c_usa[f]:.1f}%",
             xy=(f, max(c_tur[f], c_usa[f])), xytext=(40, 16),
             fontsize=14, fontweight="bold", color="#333", ha="left",
             arrowprops=dict(arrowstyle="->", color="#333", lw=1.6))

fig.text(0.045, 0.012,
         "Locked model, conditioned match by match: all 72 group results set to our locked "
         "picks except match 59 (pick was 0-1). Spain for scale.  Avraa's prediction model",
         fontsize=10, color="0.45")
fig.tight_layout(rect=(0, 0.025, 1, 1))
fig.savefig(OUT / "Turkey_scenario.png", dpi=150)
print("wrote archive/Turkey_scenario.png")
