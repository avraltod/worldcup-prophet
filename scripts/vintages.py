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


def latex_table(rows, max_rows=20):
    """Pivoted vintages table: rows = editions in play order, cols = top-5 team
    champion % + Cum.pts / Mean Brier / Cum.bits. A plain table (not longtable):
    capped at max_rows it always fits one page, and unlike a longtable it does not
    drop its continuation rows when it lands next to a float."""
    if not rows:
        return r"\textit{No editions issued yet.}"
    shown = [rows[0]] + rows[1:][-(max_rows - 1):] if len(rows) > max_rows else rows
    teams = [t for t, _ in shown[-1]["champ_top5"]]
    team_header = " & ".join(teams)
    edition_rows = []
    for r in shown:
        label = "M000 Lock" if r["fixture"] is None else f"M{r['edition']:03d} {r['fixture']}"
        champ = dict(r["champ_top5"])
        team_cells = " & ".join(
            f"{100 * champ[t]:.1f}" if t in champ else "--" for t in teams)
        cum_pts = "--" if r["cum_points"] is None else str(r["cum_points"])
        mean_b = "--" if r["mean_brier"] is None else f"{r['mean_brier']:.2f}"
        cum_b = f"{r['cum_bits']:.3f}"
        edition_rows.append(
            f"{label} & {team_cells} & {cum_pts} & {mean_b} & {cum_b} \\\\"
        )
    colspec = "l" + "r" * len(teams) + "rrr"
    note = ("" if len(shown) == len(rows) else
            f"% {len(rows) - len(shown)} intermediate editions omitted\n")
    _vin_colhdr = (f"\\makecell{{Fixture \\\\ (play order)}} & {team_header}"
                  " & Cum.\\,pts & Mean Brier & Cum.\\,bits \\\\\n")
    return (note + "\\begin{table}[!ht]\\centering\\begin{scriptsize}\n"
            "\\caption{Forecast vintages --- champion probabilities by edition "
            "(live edition M\\liveEditionNum{})}\\label{tab:live_vintages}\n"
            "\\begin{tabular}{" + colspec + "}\n"
            "\\toprule\n" + _vin_colhdr + "\\midrule\n"
            + "\n".join(edition_rows)
            + "\n\\bottomrule\n\\end{tabular}\n\\end{scriptsize}\\end{table}")
