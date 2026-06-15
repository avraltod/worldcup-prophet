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


def bracket_fig(probs, out, title, eliminated=None):
    """Two-sided knockout bracket on the submitted-entry structure (spec 3.20).
    Each box carries a team and its champion probability under `probs`
    ({team: {champion, ...}}); the submitted winners' path is shaded blue and the
    champion gold, and teams in `eliminated` (confirmed knockout losers) are
    greyed. Called once per edition with Track A and again with Track B inputs."""
    from matplotlib.patches import FancyBboxPatch
    import make_bracket_tikz as bt

    elim = set(eliminated or [])

    def cp(t):
        return probs.get(t, {}).get("champion", 0.0)

    def parents(ys):
        return [(ys[2 * i] + ys[2 * i + 1]) / 2 for i in range(len(ys) // 2)]

    rows = [15 - i for i in range(16)]
    w32 = parents(rows); r16 = parents(w32); qf = parents(r16); sf = parents(qf)
    BW, BH = 1.7, 0.62
    xL = [0, 2, 4, 6, 8]            # left half: R32, R32-winners, R16, QF, SF
    xR = [20, 18, 16, 14, 12]       # right half mirrors toward the centre
    xC = 10                         # champion column

    fig, ax = plt.subplots(figsize=(13, 7.2))
    ax.set_xlim(-0.5, 21.5); ax.set_ylim(-1.4, 17.2); ax.axis("off")

    def draw(t, x, y, side, win=False, champ=False):
        left = x if side == "L" else x - BW
        if champ:
            fc, ec, tc = "#f4d03f", "#b8860b", "black"
        elif t in elim:
            fc, ec, tc = "#ececec", "#c4c4c4", "#9a9a9a"
        elif win:
            fc, ec, tc = "#dce7f6", "#5b8fd0", "black"
        else:
            fc, ec, tc = "#f7f7f7", "#cfcfcf", "#444444"
        ax.add_patch(FancyBboxPatch((left, y - BH / 2), BW, BH,
                     boxstyle="round,pad=0.01", fc=fc, ec=ec, lw=0.8, zorder=2))
        ax.text(left + 0.08, y, bt.TEAM[t][0], va="center", ha="left",
                fontsize=7.5, color=tc,
                fontweight="bold" if champ else "normal", zorder=3)
        ax.text(left + BW - 0.08, y, f"{100 * cp(t):.0f}", va="center",
                ha="right", fontsize=6.5, color="#666666", zorder=3)

    def line(x1, y1, x2, y2):
        ax.plot([x1, x2], [y1, y2], color="#c2c2c2", lw=0.7, zorder=1)

    def connect(y1, y2, xce, xpe):
        mid = (xce + xpe) / 2
        line(xce, y1, mid, y1); line(xce, y2, mid, y2)
        line(mid, y1, mid, y2); line(mid, (y1 + y2) / 2, xpe, (y1 + y2) / 2)

    def render_side(R32, R16, QF, SF, xs, s):
        sgn = 1 if s == "L" else -1
        inner = lambda x: x + sgn * BW          # edge facing the centre
        for j, (h, a, w) in enumerate(R32):
            draw(h, xs[0], rows[2 * j], s, win=(h == w))
            draw(a, xs[0], rows[2 * j + 1], s, win=(a == w))
            connect(rows[2 * j], rows[2 * j + 1], inner(xs[0]), xs[1])
        for j, (_, _, w) in enumerate(R32):
            draw(w, xs[1], w32[j], s)
        for k in range(4):
            draw(R16[k], xs[2], r16[k], s)
            connect(w32[2 * k], w32[2 * k + 1], inner(xs[1]), xs[2])
        for k in range(2):
            draw(QF[k], xs[3], qf[k], s)
            connect(r16[2 * k], r16[2 * k + 1], inner(xs[2]), xs[3])
        draw(SF, xs[4], sf[0], s)
        connect(qf[0], qf[1], inner(xs[3]), xs[4])
        return inner(xs[4]), sf[0]

    lx, ly = render_side(bt.LEFT_R32, bt.LEFT_R16, bt.LEFT_QF, bt.LEFT_SF, xL, "L")
    rx, ry = render_side(bt.RIGHT_R32, bt.RIGHT_R16, bt.RIGHT_QF, bt.RIGHT_SF, xR, "R")

    # champion box at centre, fed by both semi-finalists
    cy = max(ly, ry) + 1.4
    draw(bt.CHAMPION, xC, cy, "L", champ=True)   # drawn with left edge = xC
    line(lx, ly, xC, ly); line(xC, ly, xC, cy - BH / 2)
    line(rx, ry, xC + BW, ry); line(xC + BW, ry, xC + BW, cy - BH / 2)
    ax.text(xC + BW / 2, cy + 0.7, "★ " + bt.TEAM[bt.CHAMPION][0],
            ha="center", fontsize=9, fontweight="bold", color="#b8860b")

    for lab, x in [("R32", xL[0]), ("R16", xL[2]), ("QF", xL[3]), ("SF", xL[4]),
                   ("SF", xR[4]), ("QF", xR[3]), ("R16", xR[2]), ("R32", xR[0])]:
        ax.text(x + (BW / 2 if x < xC else -BW / 2), 16.6, lab, ha="center",
                fontsize=8, color="#888888", fontweight="bold")
    ax.set_title(f"{title}: submitted bracket, box value = P(champion) %",
                 fontsize=10)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
    return out
