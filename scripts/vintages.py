"""Forecast vintages: one row per issued edition (M000 = the locked pre-kickoff
build). Append-only by contract — earlier rows are never modified, which is the
sanity gate that successive editions stay directly comparable."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "edition_vintages.json"


def load():
    return json.loads(PATH.read_text()) if PATH.exists() else []


def m000_row(frozen_stages):
    top5 = sorted(((t, round(d["champion"], 4)) for t, d in frozen_stages.items()),
                  key=lambda kv: -kv[1])[:5]
    return {"edition": 0, "match": None, "fixture": None, "result": None,
            "points": None, "cum_points": 0, "mean_brier": None,
            "cum_bits": 0.0, "champ_top5": [[t, p] for t, p in top5]}


def upsert(row):
    """Insert/replace the row for row['edition']; refuse to alter earlier rows."""
    rows = load()
    by_ed = {r["edition"]: r for r in rows}
    ed = row["edition"]
    if ed in by_ed and by_ed[ed] != row:
        if any(r["edition"] > ed for r in rows):
            raise ValueError(f"edition {ed} is not the latest — vintages are append-only")
    by_ed[ed] = row
    out = [by_ed[e] for e in sorted(by_ed)]
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def row_for_edition(match, entries, stats, champ_top5):
    latest = max(entries, key=lambda e: e["match"])
    return {"edition": match, "match": match, "fixture": latest["fixture"],
            "result": latest["result"], "points": latest["post"]["points"],
            "cum_points": stats["cum_points"],
            "mean_brier": round(stats["mean_brier"], 4),
            "cum_bits": round(sum(e["post"]["info_bits"] for e in entries), 4),
            "champ_top5": [[t, round(p, 4)] for t, p in champ_top5]}


def latex_table(rows, max_cols=9):
    """Vintages as a longtable: columns = M000 + the last (max_cols-1) editions;
    team rows are the latest edition's top five champions."""
    if not rows:
        return r"\textit{No editions issued yet.}"
    shown = [rows[0]] + rows[1:][-(max_cols - 1):] if len(rows) > max_cols else rows
    teams = [t for t, _ in shown[-1]["champ_top5"]]
    heads = " & ".join(f"M{r['edition']:03d}" for r in shown)
    lines = []
    for t in teams:
        cells = []
        for r in shown:
            p = dict((a, b) for a, b in r["champ_top5"]).get(t)
            cells.append(f"{100 * p:.1f}" if p is not None else "--")
        lines.append(f"{t} & " + " & ".join(cells) + r" \\")
    def _row(label, fmt, key):
        cells = []
        for r in shown:
            v = r[key]
            cells.append("--" if v is None else fmt.format(v))
        return f"{label} & " + " & ".join(cells) + r" \\"
    lines.append(r"\midrule")
    lines.append(_row("Cum. points", "{:d}", "cum_points"))
    lines.append(_row("Mean Brier", "{:.2f}", "mean_brier"))
    lines.append(_row("Cum. bits", "{:.3f}", "cum_bits"))
    colspec = "l" + "r" * len(shown)
    note = ("" if len(shown) == len(rows) else
            f"% {len(rows) - len(shown)} intermediate editions collapsed\n")
    return (note + "\\begin{longtable}{" + colspec + "}\n"
            "\\caption{Forecast vintages (all issued editions)}\\label{tab:live_vintages}\\\\\n"
            "\\toprule\n"
            "Edition & " + heads + " \\\\\n\\midrule\n\\endhead\n"
            + "\n".join(lines) + "\n\\bottomrule\n\\end{longtable}")
