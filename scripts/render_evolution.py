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


def render_paper(tex, entries):
    tex = replace_markers(tex, "LIVE-EVOLUTION-TABLE", ledger_table(entries))
    tex = replace_markers(tex, "LIVE-EVOLUTION-NARRATIVE", narrative(entries))
    return tex
