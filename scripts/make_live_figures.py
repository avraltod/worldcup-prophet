"""The two per-edition figures: current qualification odds vs the lock, and the
frozen-vs-learning champion paths. matplotlib only; Agg-safe."""
import os
os.environ.setdefault("SOURCE_DATE_EPOCH", "1749686400")  # 2026-06-12: byte-stable PDFs across reruns
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def group_qual_fig(now, groups, out):
    """4x3 grid of stacked qualification bars (Win group / 2nd / 3rd-advance /
    Out) for one track, matching the locked Figure 19 so the Frozen, Track A, and
    Track B versions are directly comparable. now[team] carries the finishing-
    position decomposition first/second/third_adv/advance_KO (from
    condition.conditional_probs); groups = {group letter: [team, ...]}."""
    WIN, SECOND, THIRD, OUT = "#0072B2", "#56B4E9", "#E69F00", "#D9D9D9"
    fig, axes = plt.subplots(4, 3, figsize=(8.2, 9.4))
    for ax, grp in zip(axes.flat, sorted(groups)):
        teams = sorted([t for t in groups[grp] if t in now],
                       key=lambda t: -now[t].get("advance_KO", 0))
        names = [t[:11] for t in teams]
        p1 = [now[t].get("first", 0) * 100 for t in teams]
        p2 = [now[t].get("second", 0) * 100 for t in teams]
        p3 = [now[t].get("third_adv", 0) * 100 for t in teams]
        qual = [now[t].get("advance_KO", 0) * 100 for t in teams]
        pout = [100 - q for q in qual]
        left3 = [a + b for a, b in zip(p1, p2)]
        left4 = [a + b for a, b in zip(left3, p3)]
        y = list(range(len(names)))[::-1]
        ax.barh(y, p1, color=WIN, label="Win group")
        ax.barh(y, p2, left=p1, color=SECOND, label="2nd")
        ax.barh(y, p3, left=left3, color=THIRD, label="3rd (advance)")
        ax.barh(y, pout, left=left4, color=OUT, label="Out")
        ax.set_yticks(y); ax.set_yticklabels(names, fontsize=7)
        ax.set_xlim(0, 100)
        ax.set_title(f"Group {grp}", fontsize=9, fontweight="bold", loc="left")
        ax.tick_params(axis="x", labelsize=6)
        for yi, q in zip(y, qual):
            ax.text(101, yi, f"{q:.0f}", va="center", fontsize=6, color="#555")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8,
               frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=[0, 0.02, 1, 1])
    fig.savefig(out, bbox_inches="tight"); plt.close(fig)


def market_fig(frozen, track_a, track_b, market, out):
    """Horizontal four-bar chart: Frozen/Track A/Track B/Market champion
    probability per team, top 12 by Track A. The single consolidated champion
    instrument: its Frozen bars are the locked 200k baseline distribution and its
    Market bars the live Polymarket snapshot, so it subsumes the separate baseline
    distribution and model-vs-market figures. Highest probability at the top, with
    Frozen on top of each team group, matching the baseline market figure."""
    teams = sorted(track_a, key=lambda t: -track_a[t]["champion"])[:12]
    n = len(teams)
    series = [
        ("Frozen", "#888888", [frozen.get(t, {}).get("champion", 0) for t in teams]),
        ("Track A", "#3b6ea5", [track_a[t]["champion"] for t in teams]),
        ("Track B", "#3d8c40", [track_b.get(t, 0) if track_b else 0 for t in teams]),
        ("Market", "#e06820", [market.get(t, 0) for t in teams]),
    ]
    height = 0.2
    offsets = [-1.5 * height, -0.5 * height, 0.5 * height, 1.5 * height]
    y = range(n)
    fig, ax = plt.subplots(figsize=(9, 7))
    for (label, color, vals), off in zip(series, offsets):
        ypos = [i + off for i in y]
        ax.barh(ypos, vals, height=height, color=color, alpha=0.85, label=label)
        for yp, v in zip(ypos, vals):
            if v > 0:
                ax.text(v + 0.002, yp, f"{100 * v:.0f}", va="center",
                        ha="left", fontsize=5, color="#333333")
    ax.set_yticks(list(y)); ax.set_yticklabels(teams, fontsize=8)
    ax.invert_yaxis()                        # highest probability at the top
    ax.set_xlabel("Champion probability")
    xmax = max((max(vals) for _, _, vals in series if vals), default=0.0)
    ax.set_xlim(0, (xmax or 0.01) * 1.12)
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


# Flag palette + schematic shapes, ported from make_bracket_tikz.draw_flag so the
# live brackets carry the same hand-drawn flags as the locked TikZ Figure 22.
_FLAGHEX = {"fr": "#CE1126", "fb": "#0033A0", "fy": "#FCD116", "fg": "#009639",
            "fk": "#000000", "fw": "#FFFFFF", "fw2": "#F2F2F2", "fo": "#F77F00",
            "fs": "#75AADB"}


def _draw_flag(ax, spec, x1, y1, x2, y2):
    """Draw the schematic flag `spec` (kind + palette colours) in rect (x1,y1)-(x2,y2)."""
    from matplotlib.patches import Rectangle, Circle, Polygon
    C = _FLAGHEX
    cx, cy, w, h = (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1

    def R(a, b, c, d, col):
        ax.add_patch(Rectangle((a, b), c - a, d - b, fc=C.get(col, col),
                               ec="none", zorder=4))
    k = spec[0]
    if k == "solid":
        R(x1, y1, x2, y2, spec[1])
    elif k == "v":
        cols = spec[1]; n = len(cols); ww = w / n
        for i, c in enumerate(cols):
            R(x1 + i * ww, y1, x1 + (i + 1) * ww, y2, c)
    elif k == "h":
        cols = spec[1]; n = len(cols); hh = h / n
        for i, c in enumerate(cols):
            R(x1, y2 - (i + 1) * hh, x2, y2 - i * hh, c)
    elif k == "hw":
        c = spec[1]; q = h / 4
        R(x1, y2 - q, x2, y2, c[0]); R(x1, y1 + q, x2, y2 - q, c[1]); R(x1, y1, x2, y1 + q, c[2])
    elif k == "vw":
        c = spec[1]; xm = x1 + w * 0.4
        R(x1, y1, xm, y2, c[0]); R(xm, y1, x2, y2, c[1])
    elif k == "plus":
        field, cr = spec[1], spec[2]; t = h * 0.30
        R(x1, y1, x2, y2, field)
        R(cx - t / 2, y1, cx + t / 2, y2, cr); R(x1, cy - t / 2, x2, cy + t / 2, cr)
    elif k == "nordic":
        field, cr = spec[1], spec[2]; t = h * 0.24; vx = x1 + w * 0.34
        R(x1, y1, x2, y2, field)
        R(vx - t / 2, y1, vx + t / 2, y2, cr); R(x1, cy - t / 2, x2, cy + t / 2, cr)
    elif k == "circle":
        R(x1, y1, x2, y2, spec[1])
        ax.add_patch(Circle((cx, cy), h * 0.32, fc=C.get(spec[2], spec[2]), ec="none", zorder=4))
    elif k == "diamond":
        f, d, c = spec[1], spec[2], spec[3]; R(x1, y1, x2, y2, f)
        ax.add_patch(Polygon([(cx, y2), (x2, cy), (cx, y1), (x1, cy)],
                             fc=C.get(d, d), ec="none", zorder=4))
        ax.add_patch(Circle((cx, cy), h * 0.18, fc=C.get(c, c), ec="none", zorder=5))
    elif k == "triangle":
        R(x1, y1, x2, y2, spec[1])
        ax.add_patch(Polygon([(x1, y2), (x1, y1), (x2, y1)],
                             fc=C.get(spec[2], spec[2]), ec="none", zorder=4))
    elif k == "canton":
        stripe, base, canton = spec[1], spec[2], spec[3]; R(x1, y1, x2, y2, base)
        n = 5; hh = h / n
        for i in range(0, n, 2):
            R(x1, y1 + i * hh, x2, y1 + (i + 1) * hh, stripe)
        R(x1, y2 - h * 0.5, x1 + w * 0.42, y2, canton)
    elif k == "crescent":
        field, cr = spec[1], spec[2]; R(x1, y1, x2, y2, field)
        ax.add_patch(Circle((cx - w * 0.04, cy), h * 0.30, fc=C.get(cr, cr), ec="none", zorder=4))
        ax.add_patch(Circle((cx + w * 0.06, cy), h * 0.26, fc=C.get(field, field), ec="none", zorder=5))
    ax.add_patch(Rectangle((x1, y1), w, h, fc="none", ec="#888888", lw=0.3, zorder=6))


def bracket_fig(probs, out, title, eliminated=None):
    """Two-sided knockout bracket on the submitted-entry structure (spec 3.20).
    Each box carries a flag (matching Figure 22), the team's 3-letter code and its
    champion probability under `probs` ({team: {champion, ...}}); the submitted
    winners' path is shaded blue and the champion gold, and teams in `eliminated`
    (confirmed knockout losers) are greyed. Called with Track A and Track B."""
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
        # schematic flag at the left of the box
        _draw_flag(ax, bt.TEAM[t][1], left + 0.07, y - 0.10, left + 0.40, y + 0.10)
        ax.text(left + 0.48, y, bt.TEAM[t][0], va="center", ha="left",
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

    # champion box, horizontally centred on xC and lifted above the two SFs
    cy = max(ly, ry) + 1.6
    draw(bt.CHAMPION, xC - BW / 2, cy, "L", champ=True)   # centred: left edge = xC - BW/2
    line(lx, ly, xC, ly); line(rx, ry, xC, ry)           # SFs in to the centre line
    line(xC, min(ly, ry), xC, cy - BH / 2)               # up to the champion box
    ax.text(xC, cy + 0.7, "★ " + bt.TEAM[bt.CHAMPION][0],
            ha="center", fontsize=9, fontweight="bold", color="#b8860b")

    for lab, x in [("R32", xL[0]), ("R16", xL[2]), ("QF", xL[3]), ("SF", xL[4]),
                   ("SF", xR[4]), ("QF", xR[3]), ("R16", xR[2]), ("R32", xR[0])]:
        ax.text(x + (BW / 2 if x < xC else -BW / 2), 16.6, lab, ha="center",
                fontsize=8, color="#888888", fontweight="bold")
    ax.set_title(f"{title}: submitted bracket, box value = P(champion) %",
                 fontsize=10)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
    return out


def mostlikely_bracket_fig(ml, probs, out, title, eliminated=None):
    """Most-likely bracket (companion to bracket_fig / Figure 19). Each R32-entry
    slot is filled by the team most likely to occupy it (ml from ml_bracket.build)
    and its box shows P(reach this slot); rounds past R32 follow the Elo
    most-likely path with boxes showing P(champion). Same geometry and flags as
    bracket_fig. `probs` supplies champion probabilities for the deeper boxes."""
    from matplotlib.patches import FancyBboxPatch
    import make_bracket_tikz as bt

    elim = set(eliminated or [])

    # Codes for teams outside the 32-team submitted bracket (bt.TEAM only covers
    # those). Interlopers can now occupy a slot or win an Elo path; they render
    # with a neutral flag box rather than a bespoke schematic flag.
    FALLBACK = {
        "South Africa": "RSA", "Qatar": "QAT", "Haiti": "HAI", "Scotland": "SCO",
        "Australia": "AUS", "Curaçao": "CUW", "Tunisia": "TUN",
        "New Zealand": "NZL", "Cape Verde": "CPV", "Saudi Arabia": "KSA",
        "Iraq": "IRQ", "Jordan": "JOR", "Congo DR": "COD", "Uzbekistan": "UZB",
        "Ghana": "GHA", "Panama": "PAN"}

    def code(t):
        return bt.TEAM[t][0] if t in bt.TEAM else FALLBACK.get(t, t[:3].upper())

    def cp(t):
        return probs.get(t, {}).get("champion", 0.0)

    def parents(ys):
        return [(ys[2 * i] + ys[2 * i + 1]) / 2 for i in range(len(ys) // 2)]

    rows = [15 - i for i in range(16)]
    w32 = parents(rows); r16 = parents(w32); qf = parents(r16); sf = parents(qf)
    BW, BH = 1.7, 0.62
    xL = [0, 2, 4, 6, 8]
    xR = [20, 18, 16, 14, 12]
    xC = 10

    fig, ax = plt.subplots(figsize=(13, 7.2))
    ax.set_xlim(-0.5, 21.5); ax.set_ylim(-1.4, 17.2); ax.axis("off")

    def draw(t, x, y, side, value, win=False, champ=False):
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
        if t in bt.TEAM:
            _draw_flag(ax, bt.TEAM[t][1], left + 0.07, y - 0.10, left + 0.40, y + 0.10)
        else:                              # neutral placeholder flag for interlopers
            ax.add_patch(FancyBboxPatch((left + 0.07, y - 0.10), 0.33, 0.20,
                         boxstyle="square,pad=0", fc="#dddddd", ec="#bbbbbb",
                         lw=0.4, zorder=3))
        ax.text(left + 0.48, y, code(t), va="center", ha="left",
                fontsize=7.5, color=tc,
                fontweight="bold" if champ else "normal", zorder=3)
        ax.text(left + BW - 0.08, y, f"{100 * value:.0f}", va="center",
                ha="right", fontsize=6.5, color="#666666", zorder=3)

    def line(x1, y1, x2, y2):
        ax.plot([x1, x2], [y1, y2], color="#c2c2c2", lw=0.7, zorder=1)

    def connect(y1, y2, xce, xpe):
        mid = (xce + xpe) / 2
        line(xce, y1, mid, y1); line(xce, y2, mid, y2)
        line(mid, y1, mid, y2); line(mid, (y1 + y2) / 2, xpe, (y1 + y2) / 2)

    def render_side(side_struct, xs, s):
        inner = lambda x: x + (1 if s == "L" else -1) * BW
        R32, R16, QF, SF = (side_struct["R32"], side_struct["R16"],
                            side_struct["QF"], side_struct["SF"])
        for j, (h, a, w, vh, va) in enumerate(R32):
            draw(h, xs[0], rows[2 * j], s, vh, win=(h == w))
            draw(a, xs[0], rows[2 * j + 1], s, va, win=(a == w))
            connect(rows[2 * j], rows[2 * j + 1], inner(xs[0]), xs[1])
        for j, (_, _, w, _, _) in enumerate(R32):
            draw(w, xs[1], w32[j], s, cp(w))
        for k in range(4):
            draw(R16[k], xs[2], r16[k], s, cp(R16[k]))
            connect(w32[2 * k], w32[2 * k + 1], inner(xs[1]), xs[2])
        for k in range(2):
            draw(QF[k], xs[3], qf[k], s, cp(QF[k]))
            connect(r16[2 * k], r16[2 * k + 1], inner(xs[2]), xs[3])
        draw(SF, xs[4], sf[0], s, cp(SF))
        connect(qf[0], qf[1], inner(xs[3]), xs[4])
        return inner(xs[4]), sf[0]

    lx, ly = render_side(ml["left"], xL, "L")
    rx, ry = render_side(ml["right"], xR, "R")

    cy = max(ly, ry) + 1.6
    champ = ml["champion"]
    draw(champ, xC - BW / 2, cy, "L", cp(champ), champ=True)
    line(lx, ly, xC, ly); line(rx, ry, xC, ry)
    line(xC, min(ly, ry), xC, cy - BH / 2)
    ax.text(xC, cy + 0.7, "★ " + code(champ),
            ha="center", fontsize=9, fontweight="bold", color="#b8860b")

    for lab, x in [("R32", xL[0]), ("R16", xL[2]), ("QF", xL[3]), ("SF", xL[4]),
                   ("SF", xR[4]), ("QF", xR[3]), ("R16", xR[2]), ("R32", xR[0])]:
        ax.text(x + (BW / 2 if x < xC else -BW / 2), 16.6, lab, ha="center",
                fontsize=8, color="#888888", fontweight="bold")
    ax.set_title(f"{title}: most-likely bracket, R32 box = P(reach slot) %, "
                 "deeper = P(champion) %", fontsize=10)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
    return out
