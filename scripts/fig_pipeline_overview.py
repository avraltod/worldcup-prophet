"""Master overview pipeline figure: two-phase architecture at a glance.

Produces paper/figs/fig_pipeline_overview.pdf.
Node vocabulary (spec §Node Visual Language):
  cylinder  + blue   = raw data object
  box       + orange = transform / model step
  ellipse   + grey   = intermediate computed value
  parallelogram + green = final output
  diamond   + white  = real-world event (match played)
"""
from pathlib import Path
import graphviz

FIGS   = Path(__file__).parent.parent / "paper" / "figs"
BLUE   = "#4472C4"
ORANGE = "#ED7D31"
GREY   = "#D9D9D9"
GREEN  = "#70AD47"

_NODE = dict(fontname="Helvetica", fontsize="9", style="filled")
_EDGE = dict(fontname="Helvetica", fontsize="8")


def build() -> graphviz.Digraph:
    g = graphviz.Digraph("pipeline_overview")
    g.attr(rankdir="LR", fontname="Helvetica", fontsize="10", bgcolor="white")
    g.attr("node", **_NODE)
    g.attr("edge", **_EDGE)

    with g.subgraph(name="cluster_inputs") as c:
        c.attr(style="dashed",
               label="Pre-tournament inputs (locked 2026-06-10)", fontsize="8")
        for nid, label in [
            ("odds",   "Bookmaker odds"),
            ("elo",    "Elo ratings"),
            ("inj",    "Injury news"),
            ("struct", "Tournament structure"),
        ]:
            c.node(nid, label, shape="cylinder",
                   fillcolor=BLUE, fontcolor="white")

    g.node("part1", "Part I:\nLocked Forecast",
           shape="box", fillcolor=ORANGE, fontcolor="white",
           width="1.6", height="0.7")

    for nid, label in [
        ("preds", "104 match predictions"),
        ("champ", "Champion probabilities"),
        ("risk",  "Risk ranking"),
    ]:
        g.node(nid, label, shape="parallelogram", fillcolor=GREEN)

    g.node("match", "Match is\nplayed", shape="diamond", fillcolor="white")

    with g.subgraph(name="cluster_live") as c:
        c.attr(style="dashed",
               label="Repeats after each of 104 matches", fontsize="8")
        c.node("espn_sb", "ESPN scoreboard API",
               shape="cylinder", fillcolor=BLUE, fontcolor="white")
        c.node("espn_bs", "ESPN box score API",
               shape="cylinder", fillcolor=BLUE, fontcolor="white")
        c.node("part2", "Part II:\nLive Prophet",
               shape="box", fillcolor=ORANGE, fontcolor="white",
               width="1.6", height="0.7")

    for nid, label in [
        ("champ_upd", "Updated champion dist."),
        ("traj",      "Two-track trajectory"),
        ("edition",   "Paper edition"),
    ]:
        g.node(nid, label, shape="parallelogram", fillcolor=GREEN)

    for src in ("odds", "elo", "inj", "struct"):
        g.edge(src, "part1")
    g.edge("part1", "preds")
    g.edge("part1", "champ")
    g.edge("part1", "risk")
    g.edge("champ",   "match")
    g.edge("match",   "part2")
    g.edge("espn_sb", "part2")
    g.edge("espn_bs", "part2")
    g.edge("part2", "champ_upd")
    g.edge("part2", "traj")
    g.edge("part2", "edition")

    return g


if __name__ == "__main__":
    FIGS.mkdir(parents=True, exist_ok=True)
    build().render(str(FIGS / "fig_pipeline_overview"), format="pdf", cleanup=True)
    print("Written:", FIGS / "fig_pipeline_overview.pdf")
