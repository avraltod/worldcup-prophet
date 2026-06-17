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
from matplotlib.lines import Line2D

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


def build(trajectory, through_match=None, out=None, issue_order=None):
    frozen = json.loads((ROOT / "data" / "frozen_stage_probs.json").read_text())
    base = {t: d["champion"] for t, d in frozen["stages"].items()}
    posts = [r for r in trajectory if r["phase"] == "post"
             and (through_match is None or r["match"] <= through_match)]
    # Order by the canonical GXXX issue order (public archive mapping) rather
    # than the trajectory append order, which disagrees with it; this keeps the
    # x-axis sequence consistent with the archive Gxxx and Tables 7/8.
    if issue_order:
        rank = {m: i for i, m in enumerate(issue_order)}
        posts = sorted(posts, key=lambda r: rank.get(r["match"], 10 ** 6))
    # x is the update index (1..n), i.e. matches played in true issue order
    # (GXXX, the trajectory's append order), NOT the schedule number (MXXX).
    # Plotting against the schedule number made the lines double back whenever
    # results were confirmed out of schedule order.
    n = len(posts)
    xs = list(range(n + 1))            # 0 = pre-tournament baseline, then 1..n
    xb = xs[1:]
    xmax = max(8, n + 2)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 9),
                                   gridspec_kw={"height_ratios": [2.0, 1.0]})
    # Colour = team; the four series share that colour and are told apart by
    # marker + line style (Frozen circle/dotted, Track A square/solid, Track B
    # diamond/dashed, Market triangle/dash-dot).
    STYLES = {
        "Frozen":  dict(ls=":",  marker="o", lw=1.3),
        "Track A": dict(ls="-",  marker="s", lw=2.0),
        "Track B": dict(ls="--", marker="D", lw=1.6),
        "Market":  dict(ls="-.", marker="^", lw=1.4),
    }
    for team, col in TEAM_COLORS.items():
        y0 = 100 * base.get(team, 0.0)
        # Frozen: flat baseline (never moves)
        ax1.plot([0, n], [y0, y0], color=col, alpha=0.5, ms=4, markevery=[0],
                 **STYLES["Frozen"])
        # Track A (result-conditioned)
        ys_a = [y0] + [100 * r["champion"].get(team, 0.0) for r in posts]
        ax1.plot(xs, ys_a, color=col, ms=4, markevery=3, **STYLES["Track A"])
        # Track B (result + Elo), when available
        ys_b = [100 * r.get("champion_b", {}).get(team, float("nan")) for r in posts]
        if any(v == v for v in ys_b):  # at least one non-nan
            ax1.plot(xb, ys_b, color=col, alpha=0.85, ms=4, markevery=3,
                     **STYLES["Track B"])
        # Market (Polymarket de-vigged), now in the team colour, when available
        ys_m = [100 * r.get("market_champion", {}).get(team, float("nan")) for r in posts]
        if any(v == v for v in ys_m):
            ax1.plot(xb, ys_m, color=col, alpha=0.85, ms=4, markevery=3,
                     **STYLES["Market"])
    ax1.axvspan(0, min(GROUP_END, xmax), color="0.93", zorder=0)
    ax1.set_xlabel("Matches played (in issue order)")
    ax1.set_ylabel("P(champion), %")
    ax1.set_xlim(0, xmax)
    ax1.set_ylim(0, max(35, 5 + max(100 * base.get(t, 0) for t in TEAM_COLORS)))
    # Two legends: team colours, and a marker/line-style key for the four series.
    team_handles = [Line2D([0], [0], color=c, lw=2.4, label=t)
                    for t, c in TEAM_COLORS.items()]
    style_handles = [Line2D([0], [0], color="0.3", ms=5, label=lbl,
                            **STYLES[lbl]) for lbl in STYLES]
    leg_teams = ax1.legend(handles=team_handles, ncol=3, frameon=False,
                           loc="upper right", fontsize=8.5, title="Team (colour)")
    ax1.add_artist(leg_teams)
    ax1.legend(handles=style_handles, ncol=1, frameon=False,
               loc="upper left", fontsize=8.5, title="Series (marker/line)")
    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    by = [r["info_bits"] for r in posts]
    ax2.bar(xb, by, width=0.6, color="#E69500", linewidth=0)
    ax2.axvspan(0, min(GROUP_END, xmax), color="0.93", zorder=0)
    ax2.set_xlabel("Matches played (in issue order)")
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
