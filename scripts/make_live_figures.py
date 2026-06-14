"""The two per-edition figures: current qualification odds vs the lock, and the
frozen-vs-learning champion paths. matplotlib only; Agg-safe."""
import os
os.environ.setdefault("SOURCE_DATE_EPOCH", "1749686400")  # 2026-06-12: byte-stable PDFs across reruns
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def group_qual_fig(frozen, now, groups, out, label="Track A", color="#3b6ea5"):
    """Horizontal bars: advance probability for `now` track, Frozen as marker.
    groups = {group letter: [team, ...]} ordering top-to-bottom.
    label/color: track label and bar color (use 'Track B' + green for second call)."""
    teams = [t for g in sorted(groups) for t in groups[g]]
    teams = [t for t in teams if t in now]
    y = range(len(teams))
    fig, ax = plt.subplots(figsize=(8, max(4, 0.28 * len(teams))))
    ax.barh(list(y), [now[t]["advance_KO"] for t in teams],
            color=color, alpha=0.85, label=label)
    ax.plot([frozen[t]["advance_KO"] for t in teams if t in frozen],
            [i for i, t in enumerate(teams) if t in frozen],
            "D", color="#888888", markersize=4, linestyle="none", label="Frozen")
    ax.set_yticks(list(y)); ax.set_yticklabels(teams, fontsize=7)
    ax.invert_yaxis(); ax.set_xlabel("P(advance to knockout)")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def champdist_fig(frozen, track_a, out, track_b=None):
    """Bar chart: champion probability Frozen/Track A/Track B, top 12 teams."""
    teams = sorted(track_a, key=lambda t: -track_a[t]["champion"])[:12]
    n = len(teams)
    has_b = bool(track_b)
    offsets = [-0.27, 0, 0.27] if has_b else [-0.18, 0.18]
    width = 0.24 if has_b else 0.35
    x = range(n)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar([i + offsets[0] for i in x],
           [frozen.get(t, {}).get("champion", 0) for t in teams],
           width=width, color="#888888", alpha=0.85, label="Frozen")
    ax.bar([i + offsets[1] for i in x],
           [track_a[t]["champion"] for t in teams],
           width=width, color="#3b6ea5", alpha=0.85, label="Track A")
    if has_b:
        ax.bar([i + offsets[2] for i in x],
               [track_b.get(t, 0) for t in teams],
               width=width, color="#3d8c40", alpha=0.85, label="Track B")
    ax.set_xticks(list(x)); ax.set_xticklabels(teams, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("P(champion)")
    ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def market_fig(frozen, track_a, track_b, market, out):
    """Four-bar chart: Frozen/Track A/Track B/Market per team, top 8 by Track A."""
    teams = sorted(track_a, key=lambda t: -track_a[t]["champion"])[:8]
    n = len(teams)
    offsets = [-0.3, -0.1, 0.1, 0.3]
    width = 0.18
    x = range(n)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = [
        ("Frozen", "#888888", [frozen.get(t, {}).get("champion", 0) for t in teams]),
        ("Track A", "#3b6ea5", [track_a[t]["champion"] for t in teams]),
        ("Track B", "#3d8c40", [track_b.get(t, 0) if track_b else 0 for t in teams]),
        ("Market", "#e06820", [market.get(t, 0) for t in teams]),
    ]
    for (label, color, vals), off in zip(bars, offsets):
        ax.bar([i + off for i in x], vals, width=width,
               color=color, alpha=0.85, label=label)
    ax.set_xticks(list(x)); ax.set_xticklabels(teams, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("P(champion)")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def two_track_fig(history, out):
    """Champion probability paths per processed match, frozen vs learning."""
    teams = sorted(history[-1]["frozen_top"],
                   key=lambda t: -history[-1]["frozen_top"][t])[:5]
    x = [h["match"] for h in history]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for t in teams:
        ax.plot(x, [h["frozen_top"].get(t) for h in history],
                "-o", markersize=3, label=f"{t} (frozen)")
        ax.plot(x, [h["learning_top"].get(t) for h in history],
                "--s", markersize=3, label=f"{t} (learning)")
    ax.set_xlabel("after match"); ax.set_ylabel("P(champion)")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
