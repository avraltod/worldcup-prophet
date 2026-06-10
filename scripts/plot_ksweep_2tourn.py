"""Regenerator for fig_ksweep_2tourn (paper Fig. 17): the two-tournament
learning-rate sweep. The per-k champion log-losses are the outputs of the two
sweep runs — `sweep_k.py` (2022) and `run_2018_ksweep.py` (2018); they are
recorded here so the figure is reproducible without re-running the (slow) sweeps.
No in-image title: the paper caption carries it (house style)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

FIGS = Path(__file__).parent.parent / "paper" / "figs"

KS = [0, 20, 40, 60, 80, 120, 160, 220, 300]
# champion log-loss at each k (from the sweep runs)
LL22 = [2.066, 1.747, 1.659, 1.778, 1.871, 1.940, 2.020, 2.163, 2.254]
LL18 = [2.626, 2.375, 2.273, 2.247, 2.251, 2.257, 2.430, 2.608, 2.882]
FZ22, FZ18 = LL22[0], LL18[0]                      # k=0 = frozen baseline
imp22 = [FZ22 - x for x in LL22]                   # improvement over frozen (higher=better)
imp18 = [FZ18 - x for x in LL18]

fig, ax = plt.subplots(figsize=(6.8, 3.7))
ax.plot(KS, imp22, "-o", color="#0072B2", lw=1.8, label="2022 (champion Argentina)")
ax.plot(KS, imp18, "-s", color="#D55E00", lw=1.8, label="2018 (champion France)")
ax.axhline(0, color="#999", lw=0.7)
ax.axvspan(40, 60, color="#2ca02c", alpha=0.10)
ax.axvline(50, color="#2ca02c", ls="--", lw=1.0)
ax.annotate("chosen default\nk = 50", (50, 0.40), textcoords="offset points",
            xytext=(6, -4), fontsize=8, color="#2ca02c")
ax.annotate("learning helps", (20, 0.05), fontsize=8, color="#666")
ax.annotate("over-reacts", (255, -0.15), fontsize=8, color="#666")
ax.set_xlabel("learning rate $k$   (k=0 = frozen)")
ax.set_ylabel("champion-forecast improvement\nover frozen (log-loss, higher=better)")
ax.legend(fontsize=8, frameon=False, loc="upper right")
fig.tight_layout()
fig.savefig(FIGS / "fig_ksweep_2tourn.png", dpi=200)
fig.savefig(FIGS / "fig_ksweep_2tourn.pdf")
print("wrote fig_ksweep_2tourn.{pdf,png}")
