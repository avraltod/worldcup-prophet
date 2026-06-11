"""Match Book: build one contemporaneous documentation entry per match from the
v2 before/after records, serialize it to a Markdown-with-frontmatter file, and
track which matches are documented. Pure: no LaTeX, no network, no git."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = ROOT / "paper" / "match_book"
FAILURE_MODES = ["champion_call", "bracket_decay", "group_upset_cascade",
                 "md3_rotation", "systematic_rating_error", "knockout_coinflip"]


def _top(dist, n=5):
    return [[t, round(p, 4)] for t, p in
            sorted(dist.items(), key=lambda kv: -kv[1])[:n]]


def _movers(pre_champ, post_champ, n=5):
    teams = set(pre_champ) & set(post_champ)
    ranked = sorted(teams, key=lambda t: -abs(post_champ[t] - pre_champ[t]))
    return [[t, round(pre_champ[t], 4), round(post_champ[t], 4)] for t in ranked[:n]]


def _watch_line(exp):
    ph = exp["probs_HDA"][0]
    fav, dog = exp["home"], exp["away"]
    return (f"an upset by {dog} would be the surprise "
            f"(model {round(ph * 100)}% {fav}).")


def build_entry(match, trajectory, expectations, forecast_commit, documented_at):
    pre = next(r for r in trajectory if r["phase"] == "pre" and r["match"] == match)
    post = next(r for r in trajectory if r["phase"] == "post" and r["match"] == match)
    exp = next(e for e in expectations if e["match"] == match)
    return {
        "match": match,
        "stage": f"Group {exp['group']}",
        "fixture": f"{exp['home']} v {exp['away']}",
        "kickoff": post["kickoff"],
        "documented_at": documented_at,
        "forecast_commit": forecast_commit,
        "failure_mode": None,
        "pre": {"pick": exp["pick"], "probs_HDA": exp["probs_HDA"],
                "market_top": _top(pre["market_champion"], 5),
                "champ_top": _top(pre["champion"], 5),
                "watch_line": _watch_line(exp)},
        "result": post["result"],
        "post": {"points": post["performance"]["points"],
                 "brier": post["performance"]["brier"],
                 "p_outcome": post["performance"]["p_outcome"],
                 "info_bits": post["info_bits"],
                 "movers": _movers(pre["champion"], post["champion"], 5)},
        "interpretation": "",
        "interpretation_source": "",
    }


def to_markdown(e):
    fm = {k: e[k] for k in ("match", "stage", "fixture", "kickoff",
                            "documented_at", "forecast_commit", "failure_mode",
                            "interpretation_source")}
    body = {"pre": e["pre"], "result": e["result"], "post": e["post"]}
    return ("---\n" + json.dumps(fm, ensure_ascii=False, indent=1) + "\n---\n\n"
            + "## DATA\n```json\n" + json.dumps(body, ensure_ascii=False, indent=1)
            + "\n```\n\n## INTERPRETATION\n" + (e["interpretation"] or "") + "\n")


def parse_markdown(text):
    _, fm_block, rest = text.split("---\n", 2)
    fm = json.loads(fm_block)
    data = json.loads(rest.split("```json\n", 1)[1].split("\n```", 1)[0])
    interp = rest.split("## INTERPRETATION\n", 1)[1].strip()
    return {**fm, **data, "interpretation": interp}


def _load_index(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else {"documented": []}


def documented_matches(path):
    return list(_load_index(path)["documented"])


def is_documented(path, match):
    return match in _load_index(path)["documented"]


def mark_documented(path, match):
    idx = _load_index(path)
    if match not in idx["documented"]:
        idx["documented"].append(match)
        idx["documented"].sort()
    Path(path).write_text(json.dumps(idx, indent=1))
