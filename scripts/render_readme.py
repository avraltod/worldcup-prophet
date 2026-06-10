"""Render the README 'Results tracking' block from the latest trajectory snapshot,
and replace only the text between the LIVE-RESULTS markers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import GROUP_FIXTURES, ROW_MATCH

START = "<!-- LIVE-RESULTS:START -->"
END = "<!-- LIVE-RESULTS:END -->"
# keyed by OFFICIAL FIFA match number (1-72), matching results_log["group"]
_NAMES = {ROW_MATCH[r]: (h, a) for r, g, h, a in GROUP_FIXTURES}


def render_results_block(trajectory, results_log):
    """Build the markdown block (string) from the last trajectory entry + the log."""
    snap = trajectory[-1]
    market = snap.get("market_champion") or {}
    lines = [
        f"_Last updated: {snap['label']} — {snap['n_played']}/104 matches played._",
        "",
        f"**Information gain in this update:** {snap['info_bits']:.3f} bits",
        "",
        "**Champion probability — model vs market (top 8):**",
        "",
        "| Team | Model | Market |",
        "|---|---|---|",
    ]
    for team, p in sorted(snap["champion"].items(), key=lambda x: -x[1])[:8]:
        mk = market.get(team)
        mk_s = f"{mk * 100:.1f}%" if mk is not None else "—"
        lines.append(f"| {team} | {p * 100:.1f}% | {mk_s} |")
    movers = snap.get("top_movers") or []
    if movers:
        lines += ["", "**Biggest moves:** " + ", ".join(
            f"{t} {'+' if d >= 0 else ''}{d}pp" for t, d in movers)]
    lines += ["", "**Recorded group results:**", ""]
    gl = results_log.get("group", {})
    for key in sorted(gl, key=lambda k: int(k)):
        h, a = _NAMES.get(int(key), ("?", "?"))
        hg, ag = gl[key]
        lines.append(f"- M{key}: {h} {hg}–{ag} {a}")
    return "\n".join(lines)


def replace_readme_block(text, block):
    """Replace text between the markers. Raises if markers are missing/duplicated."""
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("LIVE-RESULTS markers missing or duplicated")
    pre = text.split(START)[0]
    post = text.split(END, 1)[1]
    return f"{pre}{START}\n{block}\n{END}{post}"
