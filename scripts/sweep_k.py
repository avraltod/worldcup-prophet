"""k-sweep: tune the learning rate on the 2022 replay. For each k, run the
two-track replay and measure how much champion-probability the learning track's
end-of-group-stage forecast assigns to the teams that actually went deep in 2022
(Argentina champion, France runner-up). The k that best sharpens the forecast
toward the truth — without over-reacting at high k — is the default to lock."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tournament_2022 import GROUPS, BRACKET, RATINGS, TEAM_GROUP
from replay import run_replay
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent.parent
games = json.loads((ROOT / "data" / "replay_2022_games.json").read_text())
for g in games:
    g["result"] = tuple(g["result"])
STRUCT = {"groups": GROUPS, "fixtures": {g: [] for g in GROUPS}, "bracket": BRACKET}
for g in games:
    STRUCT["fixtures"][TEAM_GROUP[g["home"]]].append((g["home"], g["away"]))

CHAMP = "Argentina"
FINALISTS = ["Argentina", "France"]
KS = [0, 20, 40, 60, 80, 120, 160, 220, 300]
N = 3000

print(f"{'k':>4}  {'P(champ Arg)':>12}  {'P(finalists)':>12}  {'champ log-loss':>14}  {'mean |drift|':>12}")
rows = []
for k in KS:
    traj = run_replay(STRUCT, RATINGS, games, N=N, seed=2022, k=k)
    d = traj["learning"][-1]["champion"]
    champ = d[CHAMP]
    fin = sum(d[t] for t in FINALISTS)
    ll = -math.log(max(champ, 1e-9))
    # responsiveness: how far the learning forecast drifted from the frozen one
    fz = traj["frozen"][-1]["champion"]
    move = sum(abs(d[t] - fz[t]) for t in d) / 2  # total variation distance
    rows.append((k, champ, fin, ll, move))
    print(f"{k:>4}  {champ*100:>11.1f}%  {fin*100:>11.1f}%  {ll:>14.3f}  {move*100:>11.1f}%")

best_fin = max(rows, key=lambda r: r[2])
best_ll = min(rows, key=lambda r: r[3])
print(f"\nfrozen baseline (k=0):  finalists {rows[0][2]*100:.1f}%   champ log-loss {rows[0][3]:.3f}")
print(f"best by finalist-mass:  k={best_fin[0]}  (finalists {best_fin[2]*100:.1f}%)")
print(f"best by champ log-loss: k={best_ll[0]}  (log-loss {best_ll[3]:.3f})")

# figure
ks = [r[0] for r in rows]
fig, ax1 = plt.subplots(figsize=(6.6, 3.7))
ax1.plot(ks, [r[2] * 100 for r in rows], "-o", color="#0072B2",
         label="P(eventual finalists: Arg + Fra)")
ax1.set_xlabel("learning rate $k$   (k=0 = frozen track)")
ax1.set_ylabel("finalist champion-prob mass (%)", color="#0072B2")
ax1.axvline(best_fin[0], color="#999", ls="--", lw=0.8)
ax2 = ax1.twinx()
ax2.plot(ks, [r[4] * 100 for r in rows], "-s", color="#E69F00", alpha=0.8,
         label="forecast move vs frozen (TV dist.)")
ax2.set_ylabel("learning-vs-frozen move (%)", color="#E69F00")
ax1.set_title("k sweep: does learning sharpen the 2022 forecast toward the truth?",
              fontsize=10, loc="left")
fig.tight_layout()
fig.savefig(ROOT / "paper" / "figs" / "fig_ksweep.png", dpi=200)
fig.savefig(ROOT / "paper" / "figs" / "fig_ksweep.pdf")
print("wrote paper/figs/fig_ksweep.{png,pdf}")
