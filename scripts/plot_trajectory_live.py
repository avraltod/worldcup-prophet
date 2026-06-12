"""Generate paper/figs/fig_trajectory_live.pdf — the realized forecast
trajectory for the live editions: champion probabilities after every recorded
result (top panel) and per-result information in bits (bottom panel), in the
same visual language as fig_trajectory_demo. Importable: build(trajectory,
through_match) draws POST records with match <= through_match."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "paper" / "figs"

TEAM_COLORS = {
    "Spain": "#d62728",
    "Argentina": "#7fb3e0",
    "France": "#1f5fa8",
    "Portugal": "#2ca02c",
    "England": "#222222",
    "Brazil": "#f0b000",
}
GROUP_END = 72


def build(trajectory, through_match=None, out=None):
    frozen = json.loads((ROOT / "data" / "frozen_stage_probs.json").read_text())
    base = {t: d["champion"] for t, d in frozen["stages"].items()}
    posts = [r for r in trajectory if r["phase"] == "post"
             and (through_match is None or r["match"] <= through_match)]
    xs = [0] + [r["match"] for r in posts]
    xmax = max(8, xs[-1] + 2)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 9),
                                   gridspec_kw={"height_ratios": [2.0, 1.0]})
    for team, col in TEAM_COLORS.items():
        ys = [100 * base.get(team, 0.0)] + \
             [100 * r["champion"].get(team, 0.0) for r in posts]
        ax1.plot(xs, ys, color=col, lw=2.2, label=team, marker="o", ms=4)
    ax1.axvspan(0, min(GROUP_END, xmax), color="0.93", zorder=0)
    ax1.set_xlabel("Matches played")
    ax1.set_ylabel("P(champion), %")
    ax1.set_xlim(0, xmax)
    ax1.set_ylim(0, max(35, 5 + max(100 * base.get(t, 0) for t in TEAM_COLORS)))
    ax1.legend(ncol=3, frameon=False, loc="upper right", fontsize=10)
    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    bx = [r["match"] for r in posts]
    by = [r["info_bits"] for r in posts]
    ax2.bar(bx, by, width=0.6, color="#E69500", linewidth=0)
    ax2.axvspan(0, min(GROUP_END, xmax), color="0.93", zorder=0)
    ax2.set_xlabel("Matches played")
    ax2.set_ylabel("Info gained\n(bits)")
    ax2.set_xlim(0, xmax)
    ax2.set_ylim(0, max(0.05, max(by) * 1.3 if by else 0.05))
    ax2.set_title("Information content per match (orange = group stage)",
                  fontsize=12, loc="left")
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.tight_layout()
    out = Path(out) if out else (FIGS / "fig_trajectory_live.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    fig.savefig(Path(str(out).replace(".pdf", ".png")), dpi=150)
    plt.close(fig)
    return out


if __name__ == "__main__":
    traj = json.loads((ROOT / "data" / "trajectory_v2.json").read_text())
    print("wrote", build(traj))
