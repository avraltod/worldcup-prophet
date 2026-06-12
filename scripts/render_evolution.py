"""Render the living LaTeX from Match Book entries: a results ledger table (all
matches) and a narrative that highlights only the informative ones. Marker
replacement is guarded so only the delimited regions are ever written; frozen_hash
lets the driver prove the rest of the .tex is untouched. Pure."""
import hashlib
import re as _re

INFORMATIVE_BITS = 0.05   # matches above this, or with a failure mode, get prose


def _markers(name):
    return f"% {name}:START", f"% {name}:END"


def replace_markers(tex, name, content):
    start, end = _markers(name)
    if start not in tex or end not in tex:
        raise ValueError(f"missing markers for {name}")
    if tex.index(start) > tex.index(end):
        raise ValueError(f"marker {name}:START appears after :END")
    pre = tex.split(start, 1)[0]
    post = tex.split(end, 1)[1]
    return f"{pre}{start}\n{content}\n{end}{post}"


def frozen_hash(tex):
    """Hash everything OUTSIDE every LIVE-EVOLUTION marker block."""
    stripped = _re.sub(r"% (LIVE-EVOLUTION-[A-Z]+):START.*?% \1:END",
                       "", tex, flags=_re.DOTALL)
    return hashlib.sha256(stripped.encode()).hexdigest()


def _score(result):
    return f"{result[0]}--{result[1]}"


def ledger_table(entries):
    if not entries:
        return r"\textit{No matches documented yet.}"
    rows = []
    for e in entries:
        fm = e["failure_mode"] or "--"
        rows.append(
            f"{e['match']} & {e['fixture']} & {e['pre']['pick'][0]}--{e['pre']['pick'][1]} "
            f"& {_score(e['result'])} & {e['post']['points']} & {e['post']['brier']:.3f} "
            f"& {e['post']['info_bits']:.3f} & {fm} \\\\")
    head = ("\\begin{longtable}{rlcccccl}\n"
            "\\toprule\n"
            "M & Fixture & Pick & Result & Pts & Brier & Info & Mode \\\\\n"
            "\\midrule\n"
            "\\endhead\n")
    foot = "\n\\bottomrule\n\\end{longtable}"
    return head + "\n".join(rows) + foot


def narrative(entries):
    picked = [e for e in entries
              if e["post"]["info_bits"] >= INFORMATIVE_BITS or e["failure_mode"]]
    if not picked:
        return "No individually decisive results yet; see the ledger for the full record."
    out = []
    for e in picked:
        out.append(f"\\textbf{{M{e['match']} ({e['fixture']}).}} {e['interpretation']}")
    return "\n\n".join(out)


def _pct(x):
    return f"{100 * x:.1f}"


def _delta(a, b):
    d = 100 * (b - a)
    return f"$+{d:.1f}$" if d >= 0.05 else (f"$-{abs(d):.1f}$" if d <= -0.05 else "0.0")


def divergence_section(frozen, now, entries, group_state):
    """Frozen-vs-conditional stage probabilities and revealed group state.
    frozen/now: {team: {advance_KO, R16, QF, SF, final, champion}};
    group_state: [{group, played, total, rows: [(team, pts, gd)]}]. Pure."""
    if not entries:
        return r"\textit{No matches revealed yet; the conditional forecast equals the baseline.}"
    n_results = len(entries)
    bits = sum(e["post"]["info_bits"] for e in entries)

    top = sorted(frozen, key=lambda t: -frozen[t]["champion"])[:10]
    movers = [t for t in now
              if t in frozen
              and (abs(now[t]["advance_KO"] - frozen[t]["advance_KO"]) >= 0.03
                   or abs(now[t]["champion"] - frozen[t]["champion"]) >= 0.005)]
    teams = sorted(set(top) | set(movers), key=lambda t: -now.get(t, frozen[t])["champion"])

    rows = []
    for t in teams:
        f, c = frozen[t], now.get(t, frozen[t])
        rows.append(
            f"{t} & {_pct(f['champion'])} & {_pct(c['champion'])} & {_delta(f['champion'], c['champion'])}"
            f" & {_pct(f['advance_KO'])} & {_pct(c['advance_KO'])} & {_delta(f['advance_KO'], c['advance_KO'])} \\\\")
    table = (
        "\\begin{longtable}{lrrrrrr}\n\\toprule\n"
        " & \\multicolumn{3}{c}{Champion (\\%)} & \\multicolumn{3}{c}{Advance (\\%)} \\\\\n"
        "\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}\n"
        "Team & frozen & now & $\\Delta$ & frozen & now & $\\Delta$ \\\\\n"
        "\\midrule\n\\endhead\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{longtable}")

    gs = []
    for g in group_state:
        line = "; ".join(f"{t} {pts} pts ({'+' if gd >= 0 else ''}{gd})"
                         for t, pts, gd in g["rows"])
        gs.append(f"\\textit{{Group {g['group']}}} ({g['played']} of {g['total']} played): {line}.")
    group_par = ("\n\n" + "\n".join(gs)) if gs else ""

    intro = (f"With {n_results} of 104 results revealed ({bits:.3f} bits of championship "
             f"information), the conditional forecast diverges from the locked baseline "
             f"as follows. The table lists the baseline top ten plus any team whose "
             f"advance probability moved by at least three percentage points or whose "
             f"champion probability moved by at least half a point; the frozen column "
             f"is fixed for the whole tournament, so successive versions of this table "
             f"are directly comparable.")
    return intro + "\n\n" + table + group_par


def render_paper(tex, entries, frozen=None, now=None, group_state=None):
    tex = replace_markers(tex, "LIVE-EVOLUTION-TABLE", ledger_table(entries))
    tex = replace_markers(tex, "LIVE-EVOLUTION-NARRATIVE", narrative(entries))
    if frozen is not None and now is not None:
        tex = replace_markers(tex, "LIVE-EVOLUTION-DIVERGENCE",
                              divergence_section(frozen, now, entries, group_state or []))
    return tex
