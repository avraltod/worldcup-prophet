"""The two per-edition figures: current qualification odds vs the lock, and the
frozen-vs-learning champion paths. matplotlib only; Agg-safe."""
import os
os.environ.setdefault("SOURCE_DATE_EPOCH", "1749686400")  # 2026-06-12: byte-stable PDFs across reruns
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def group_qual_fig(frozen, now, groups, out):
    """Horizontal bars: advance probability now, with the lock as a marker.
    groups = {group letter: [team, ...]} ordering top-to-bottom."""
    teams = [t for g in sorted(groups) for t in groups[g]]
    teams = [t for t in teams if t in now]
    y = range(len(teams))
    fig, ax = plt.subplots(figsize=(8, max(4, 0.28 * len(teams))))
    ax.barh(list(y), [now[t]["advance_KO"] for t in teams],
            color="#3b6ea5", alpha=0.85, label="now")
    ax.plot([frozen[t]["advance_KO"] for t in teams if t in frozen],
            [i for i, t in enumerate(teams) if t in frozen],
            "D", color="#d08415", markersize=4, linestyle="none", label="lock")
    ax.set_yticks(list(y)); ax.set_yticklabels(teams, fontsize=7)
    ax.invert_yaxis(); ax.set_xlabel("P(advance to knockout)")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def champdist_fig(frozen, now, out):
    """Bar chart: champion probability now vs frozen lock, top 12 teams."""
    teams = sorted(now, key=lambda t: -now[t]["champion"])[:12]
    x = range(len(teams))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar([i - 0.18 for i in x], [frozen.get(t, {}).get("champion", 0) for t in teams],
           width=0.35, color="#d08415", alpha=0.85, label="lock")
    ax.bar([i + 0.18 for i in x], [now[t]["champion"] for t in teams],
           width=0.35, color="#3b6ea5", alpha=0.85, label="now")
    ax.set_xticks(list(x)); ax.set_xticklabels(teams, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("P(champion)")
    ax.legend(fontsize=9)
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
