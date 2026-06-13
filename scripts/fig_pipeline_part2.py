"""Part II — Live Prophet pipeline figure (detail, top-to-bottom).

Layout: ingestion → performance signal → two-track split (A frozen / B learning)
→ convergence (KL divergence + outputs). A dashed feedback arrow from Track B's
updated ratings back to current ratings signals the cross-match accumulation.
Produces paper/figs/fig_pipeline_part2.pdf.
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
    g = graphviz.Digraph("pipeline_part2")
    g.attr(rankdir="TB", fontname="Helvetica", fontsize="10", bgcolor="white")
    g.attr("node", **_NODE)
    g.attr("edge", **_EDGE)

    with g.subgraph(name="cluster_outer") as outer:
        outer.attr(style="dashed",
                   label="Repeats after each of 104 matches", fontsize="9")

        # Ingestion
        with outer.subgraph(name="cluster_ingest") as c:
            c.attr(label="Ingestion", style="solid", fontsize="8")
            c.node("espn_sb",  "ESPN scoreboard API",
                   shape="cylinder", fillcolor=BLUE, fontcolor="white")
            c.node("parse_sb", "Parse scoreboard:\nmap to FIFA match no.",
                   shape="box", fillcolor=ORANGE, fontcolor="white")
            c.node("result",   "result (h, a)",
                   shape="ellipse", fillcolor=GREY)
            c.node("espn_bs",  "ESPN box score API",
                   shape="cylinder", fillcolor=BLUE, fontcolor="white")
            c.node("parse_bs", "Parse box score:\nSoT, off-target, blocked",
                   shape="box", fillcolor=ORANGE, fontcolor="white")
            c.node("shots",    "shot stats",
                   shape="ellipse", fillcolor=GREY)
            c.edge("espn_sb",  "parse_sb")
            c.edge("parse_sb", "result")
            c.edge("espn_bs",  "parse_bs")
            c.edge("parse_bs", "shots")

        # Performance signal
        with outer.subgraph(name="cluster_perf") as c:
            c.attr(label="Performance signal", style="solid", fontsize="8")
            c.node("proxy_xg",   "Proxy xG:\n0.3256 × SoT",
                   shape="box", fillcolor=ORANGE, fontcolor="white")
            c.node("lambda_obs", "λ_obs (home, away)",
                   shape="ellipse", fillcolor=GREY)
            c.node("ratings",    "current ratings R_i^eff",
                   shape="ellipse", fillcolor=GREY)
            c.node("elo_fit",    "Elo synthesis\n→ fit_rates",
                   shape="box", fillcolor=ORANGE, fontcolor="white")
            c.node("lambda_exp", "λ_exp (home, away)",
                   shape="ellipse", fillcolor=GREY)
            c.node("net_surp",
                   "Net surprise:\ns = (λ_obs_H−λ_exp_H)\n  −(λ_obs_A−λ_exp_A)",
                   shape="box", fillcolor=ORANGE, fontcolor="white")
            c.node("s_sig",      "surprise signal s\n(zero-sum)",
                   shape="ellipse", fillcolor=GREY)
            c.edge("shots",      "proxy_xg")
            c.edge("proxy_xg",   "lambda_obs")
            c.edge("ratings",    "elo_fit")
            c.edge("elo_fit",    "lambda_exp")
            c.edge("lambda_obs", "net_surp")
            c.edge("lambda_exp", "net_surp")
            c.edge("net_surp",   "s_sig")

        # Track A — Frozen
        with outer.subgraph(name="cluster_track_a") as c:
            c.attr(label="Track A — Frozen", style="solid", fontsize="8")
            c.node("frozen_sim",
                   "Conditional re-sim:\n50k tournaments\nresults pinned",
                   shape="box", fillcolor=ORANGE, fontcolor="white")
            c.node("p_frozen", "p_t^frozen",
                   shape="ellipse", fillcolor=GREY)
            c.edge("frozen_sim", "p_frozen")

        # Track B — Learning
        with outer.subgraph(name="cluster_track_b") as c:
            c.attr(label="Track B — Learning", style="solid", fontsize="8")
            c.node("drift_upd",
                   "Drift update:\nd ← 0.95·d + clip(50·s, ±75)",
                   shape="box", fillcolor=ORANGE, fontcolor="white")
            c.node("upd_ratings", "updated ratings\nR_i + d_i",
                   shape="ellipse", fillcolor=GREY)
            c.node("learn_sim",
                   "Conditional re-sim:\n50k tournaments\nresults pinned",
                   shape="box", fillcolor=ORANGE, fontcolor="white")
            c.node("p_learn", "p_t^learn",
                   shape="ellipse", fillcolor=GREY)
            c.edge("drift_upd",   "upd_ratings")
            c.edge("upd_ratings", "learn_sim")
            c.edge("learn_sim",   "p_learn")

        # Convergence
        with outer.subgraph(name="cluster_conv") as c:
            c.attr(label="Convergence", style="solid", fontsize="8")
            c.node("kl_div",   "KL divergence:\nD_KL(p_t ‖ p_{t−1})",
                   shape="box", fillcolor=ORANGE, fontcolor="white")
            c.node("info_led", "per-game information\nledger (bits)",
                   shape="parallelogram", fillcolor=GREEN)
            c.node("champ_tr", "two-track champion\ntrajectory",
                   shape="parallelogram", fillcolor=GREEN)
            c.node("paper_ed", "paper edition\n(LaTeX live units)",
                   shape="parallelogram", fillcolor=GREEN)
            c.edge("kl_div", "info_led")

        # Cross-subgraph edges
        outer.edge("result",   "frozen_sim")
        outer.edge("s_sig",    "frozen_sim", label="(ignored in A)")
        outer.edge("result",   "drift_upd")
        outer.edge("s_sig",    "drift_upd")
        outer.edge("p_frozen", "kl_div")
        outer.edge("p_learn",  "kl_div")
        outer.edge("p_frozen", "champ_tr")
        outer.edge("p_learn",  "champ_tr")
        outer.edge("p_frozen", "paper_ed")
        outer.edge("p_learn",  "paper_ed")

    # Dashed feedback: cross-match dependency (not a within-diagram cycle)
    g.edge("upd_ratings", "ratings",
           label="next match", style="dashed", constraint="false")

    return g


if __name__ == "__main__":
    FIGS.mkdir(parents=True, exist_ok=True)
    build().render(str(FIGS / "fig_pipeline_part2"), format="pdf", cleanup=True)
    print("Written:", FIGS / "fig_pipeline_part2.pdf")
