"""Part I — Locked Forecast pipeline figure (detail, left-to-right railway).

Two input lanes merge at (λ_H, λ_A), then split into:
  Branch A → EV-optimal match prediction
  Branch B → Monte Carlo → slot emergence + ML risk
Produces paper/figs/fig_pipeline_part1.pdf.
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
    g = graphviz.Digraph("pipeline_part1")
    g.attr(rankdir="LR", fontname="Helvetica", fontsize="10", bgcolor="white")
    g.attr("node", **_NODE)
    g.attr("edge", **_EDGE)

    # Lane 1: group matches (market-driven)
    with g.subgraph(name="cluster_lane1") as c:
        c.attr(style="dashed", fontsize="8",
               label="Group matches (55 fixtures with market odds)")
        c.node("odds_json", "Bookmaker odds JSON\n(o_H, o_D, o_A)",
               shape="cylinder", fillcolor=BLUE, fontcolor="white")
        c.node("devig", "De-vig:\nnormalize 1/o_j",
               shape="box", fillcolor=ORANGE, fontcolor="white")
        c.node("fair1", "fair probs\n(p_H, p_D, p_A)",
               shape="ellipse", fillcolor=GREY)
        c.edge("odds_json", "devig", label="normalize")
        c.edge("devig",     "fair1")

    # Lane 2: KO + odds-free (Elo-driven)
    with g.subgraph(name="cluster_lane2") as c:
        c.attr(style="dashed", fontsize="8",
               label="Knockout + 17 odds-free group fixtures")
        c.node("elo_inj", "Elo ratings +\ninjury adj.",
               shape="cylinder", fillcolor=BLUE, fontcolor="white")
        c.node("elo_synth", "Elo synthesis:\nlogistic + draw share",
               shape="box", fillcolor=ORANGE, fontcolor="white")
        c.node("fair2", "fair probs\n(p_H, p_D, p_A)",
               shape="ellipse", fillcolor=GREY)
        c.edge("elo_inj",   "elo_synth")
        c.edge("elo_synth", "fair2")

    # Shared: Poisson inversion
    g.node("fit_rates",
           "Poisson inversion:\ngrid search λ\n(step 0.05, total∈[1.6,3.4])",
           shape="box", fillcolor=ORANGE, fontcolor="white")
    g.node("lambda", "goal rate pair\n(λ_H, λ_A)",
           shape="ellipse", fillcolor=GREY)

    g.edge("fair1", "fit_rates", label="grid search")
    g.edge("fair2", "fit_rates", label="grid search")
    g.edge("fit_rates", "lambda")

    # Branch A: match prediction
    g.node("ev_pick", "EV-optimal pick:\nargmax E[S]\nover 9×9 grid",
           shape="box", fillcolor=ORANGE, fontcolor="white")
    g.node("match_pred", "match prediction\n(ĥ, â)  ×104",
           shape="parallelogram", fillcolor=GREEN)
    g.edge("lambda",   "ev_pick")
    g.edge("ev_pick",  "match_pred")

    # Branch B: simulation tree
    g.node("mc",
           "Monte Carlo:\n200k tournaments\n(Poisson group scores\n+ Elo KO Bernoulli\n+ FIFA tiebreakers)",
           shape="box", fillcolor=ORANGE, fontcolor="white")
    g.node("slot_em", "Slot emergence:\nargmax P(team\nwins slot m)",
           shape="box", fillcolor=ORANGE, fontcolor="white")
    g.node("bracket", "bracket picks +\nchampion probs",
           shape="parallelogram", fillcolor=GREEN)
    g.node("ml_risk", "ML risk:\nRF + XGBoost + SHAP\n40k draws",
           shape="box", fillcolor=ORANGE, fontcolor="white")
    g.node("risk_out", "per-call\nrisk ranking",
           shape="parallelogram", fillcolor=GREEN)

    g.edge("lambda",   "mc",       label="Poisson sample")
    g.edge("mc",       "slot_em")
    g.edge("slot_em",  "bracket")
    g.edge("mc",       "ml_risk")
    g.edge("ml_risk",  "risk_out")

    # Dashed handoff to Part II
    g.node("to_p2", "→ baseline\nfor Part II",
           shape="plaintext", style="", fillcolor="white")
    g.edge("lambda", "to_p2", style="dashed")

    return g


if __name__ == "__main__":
    FIGS.mkdir(parents=True, exist_ok=True)
    build().render(str(FIGS / "fig_pipeline_part1"), format="pdf", cleanup=True)
    print("Written:", FIGS / "fig_pipeline_part1.pdf")
