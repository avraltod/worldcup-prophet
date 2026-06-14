"""Pure LaTeX builders for the living layer, consumed by render_live: the
results ledger table, the narrative of informative matches, the divergence
section, the conditional champion table, and the trajectory figure. The
driver writes these to paper/live/*.tex via render_live.write_unit; nothing
here touches the skeleton. Pure."""

INFORMATIVE_BITS = 0.05   # matches above this, or with a failure mode, get prose


def _score(result):
    return f"{result[0]}--{result[1]}"


def ledger_table(entries):
    if not entries:
        return r"\textit{No matches documented yet.}"
    rows = []
    for e in entries:
        fm = (e["failure_mode"] or "--").replace("_", r"\_")
        played = e.get("result") is not None
        pick_a = "--" if played else f"{e['pre']['pick'][0]}--{e['pre']['pick'][1]}"
        pick_b = "--" if played else pick_a  # Track B scoreline shown when KO upcoming
        rows.append(
            f"{e['match']} & {e['fixture']} & {e['pre']['pick'][0]}--{e['pre']['pick'][1]} "
            f"& {pick_a} & {pick_b} "
            f"& {_score(e['result'])} & {e['post']['points']} & {e['post']['brier']:.3f} "
            f"& {e['post']['info_bits']:.3f} & {fm} \\\\")
    _hdr = ("M & Fixture & Frozen & Track~A & Track~B & Result & Pts & Brier & Info & Mode \\\\\n")
    head = ("\\begin{scriptsize}\n"
            "\\begin{longtable}{rlcccccccl}\n"
            "\\caption{Match record (live edition)}\\label{tab:live_ledger}\\\\\n"
            "\\toprule\n" + _hdr + "\\midrule\n"
            "\\endfirsthead\n"
            "\\toprule\n" + _hdr + "\\midrule\n"
            "\\endhead\n")
    foot = "\n\\bottomrule\n\\end{longtable}\n\\end{scriptsize}"
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


def divergence_section(frozen, now, entries, group_state, champion_b=None, now_b=None):
    """Frozen-vs-conditional stage probabilities and revealed group state.
    frozen/now: {team: {advance_KO, R16, QF, SF, final, champion}};
    group_state: [{group, played, total, rows: [{team, P, W, D, L, GF, GA, Pts}]}];
    champion_b: {team: float} Track B champion probability (optional).
    now_b: {team: {advance_KO, ...}} Track B full stage probs (optional). Pure."""
    if not entries:
        return r"\textit{No matches revealed yet; the conditional forecast equals the baseline.}"
    n_results = len(entries)
    bits = sum(e["post"]["info_bits"] for e in entries)

    top = sorted(frozen, key=lambda t: -frozen[t]["champion"])[:10]
    movers = [t for t in now
              if t in frozen
              and (abs(now[t]["advance_KO"] - frozen[t]["advance_KO"]) >= 0.03
                   or abs(now[t]["champion"] - frozen[t]["champion"]) >= 0.005)]
    # tiebreak on the name: equal champion probs (e.g. two teams at 0 in the
    # MC sample) must not inherit set-iteration order, which varies per process
    teams = sorted(set(top) | set(movers),
                   key=lambda t: (-now.get(t, frozen[t])["champion"], t))

    has_b_champ = bool(champion_b)
    has_b_adv = bool(now_b)
    has_b = has_b_champ  # whether to show Track B champion column
    rows = []
    for t in teams:
        f, c = frozen[t], now.get(t, frozen[t])
        if has_b_champ:
            b_champ = champion_b.get(t)
            b_champ_str = _pct(b_champ) if b_champ is not None else "---"
        if has_b_adv and t in now_b:
            b_adv = now_b[t].get("advance_KO", 0.0)
            b_adv_str = _pct(b_adv)
        elif has_b_champ:
            b_adv_str = "---"
        if has_b_champ and has_b_adv:
            rows.append(
                f"{t} & {_pct(f['champion'])} & {_pct(c['champion'])} & {b_champ_str} & "
                f"{_delta(f['champion'], c['champion'])}"
                f" & {_pct(f['advance_KO'])} & {_pct(c['advance_KO'])} & {b_adv_str} & "
                f"{_delta(f['advance_KO'], c['advance_KO'])} \\\\")
        elif has_b_champ:
            rows.append(
                f"{t} & {_pct(f['champion'])} & {_pct(c['champion'])} & {b_champ_str} & "
                f"{_delta(f['champion'], c['champion'])}"
                f" & {_pct(f['advance_KO'])} & {_pct(c['advance_KO'])} & "
                f"{_delta(f['advance_KO'], c['advance_KO'])} \\\\")
        else:
            rows.append(
                f"{t} & {_pct(f['champion'])} & {_pct(c['champion'])} & "
                f"{_delta(f['champion'], c['champion'])}"
                f" & {_pct(f['advance_KO'])} & {_pct(c['advance_KO'])} & "
                f"{_delta(f['advance_KO'], c['advance_KO'])} \\\\")
    if has_b_champ and has_b_adv:
        col_spec = "lrrrrrrrr"
        champ_span = "\\multicolumn{4}{c}{Champion (\\%)}"
        champ_rule = "\\cmidrule(lr){2-5}"
        adv_span = "\\multicolumn{4}{c}{Advance (\\%)}"
        adv_rule = "\\cmidrule(lr){6-9}"
        col_header = (
            "Team & Frozen & Track~A & Track~B & $\\Delta$ (A$-$Frozen) & "
            "Frozen & Track~A & Track~B & $\\Delta$ \\\\\n"
        )
    elif has_b_champ:
        col_spec = "lrrrrrrr"
        champ_span = "\\multicolumn{4}{c}{Champion (\\%)}"
        champ_rule = "\\cmidrule(lr){2-5}"
        adv_span = "\\multicolumn{3}{c}{Advance (\\%)}"
        adv_rule = "\\cmidrule(lr){6-8}"
        col_header = (
            "Team & Frozen & Track~A & Track~B & $\\Delta$ (A$-$Frozen) & "
            "Frozen & Track~A & $\\Delta$ \\\\\n"
        )
    else:
        col_spec = "lrrrrrr"
        champ_span = "\\multicolumn{3}{c}{Champion (\\%)}"
        champ_rule = "\\cmidrule(lr){2-4}"
        adv_span = "\\multicolumn{3}{c}{Advance (\\%)}"
        adv_rule = "\\cmidrule(lr){5-7}"
        col_header = "Team & Frozen & Track~A & $\\Delta$ & Frozen & Track~A & $\\Delta$ \\\\\n"
    _div_subhdr = (f" & {champ_span} & {adv_span} \\\\\n"
                  f"{champ_rule}{adv_rule}\n" + col_header + "\\midrule\n")
    table = (
        "\\begin{footnotesize}\n"
        f"\\begin{{longtable}}{{{col_spec}}}\n"
        "\\caption{Champion and advance probability divergence from the locked baseline "
        "(live edition)}\\label{tab:live_divergence}\\\\\n"
        "\\toprule\n"
        + _div_subhdr
        + "\\endfirsthead\n"
        "\\toprule\n"
        + _div_subhdr
        + "\\endhead\n"
        + "\n".join(rows)
        + "\n\\bottomrule\n\\end{longtable}\n\\end{footnotesize}")

    gs = []
    for g in group_state:
        line = "; ".join(
            f"{r['team']} {r['Pts']} pts ({'+' if r['GF'] - r['GA'] >= 0 else ''}{r['GF'] - r['GA']})"
            for r in g["rows"])
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


def champ_table(frozen, now, n_results, champion_b=None):
    """Headline probability table, top 8 by current champion probability.
    When champion_b is a non-empty dict, adds Track A / Track B / Δ columns."""
    teams = sorted(now, key=lambda t: -now[t]["champion"])[:8]
    has_b = bool(champion_b)
    rows = []
    for t in teams:
        f = frozen.get(t, {"champion": 0.0})
        c = now[t]
        if has_b:
            b = champion_b.get(t)
            delta = 100 * (c["champion"] - f["champion"])   # Track A − Frozen
            b_str = f"{100*b:.1f}\\%" if b is not None else "---"
            rows.append(
                f"      {t:<14} & {100*f['champion']:.1f}\\% & "
                f"{100*c['champion']:.1f}\\% & {b_str} & "
                f"{delta:+.1f} & "
                f"{100*c['final']:.1f}\\% & {100*c['SF']:.1f}\\% & "
                f"{100*c.get('QF', 0.0):.1f}\\% \\\\"
            )
        else:
            rows.append(
                f"      {t:<14} & {100*f['champion']:.1f}\\% & "
                f"{100*c['champion']:.1f}\\% & {100*c['final']:.1f}\\% & "
                f"{100*c['SF']:.1f}\\% \\\\"
            )
    if has_b:
        col_spec = "lccccccc"
        header = (
            "      Team & Frozen (\\%) & Track~A (\\%) & Track~B (\\%) & "
            "$\\Delta$ (A$-$Frozen) & Finalist (now) & Semi (now) & QF (now) \\\\"
        )
        note = (
            f"Frozen = pre-kickoff lock ($N$ = 200{{,}}000, "
            f"\\texttt{{data/frozen\\_stage\\_probs.json}}), never changes; "
            f"Track~A = result-conditioned, June~10 ratings "
            f"($N$ = 50{{,}}000, seed 2026); "
            f"Track~B = result-conditioned + live Elo + bookmaker odds + lineup adj."
        )
    else:
        col_spec = "lcccc"
        header = (
            "      Team & Champion (Frozen) & Champion (Track~A) & "
            "Finalist (Track~A) & Semi-finalist (Track~A) \\\\"
        )
        note = (
            f"Track~A columns conditioned on the {n_results} results "
            f"revealed to date ($N$ = 50{{,}}000, seed 2026); "
            f"Frozen = $N$ = 200{{,}}000 pre-kickoff baseline "
            f"(\\texttt{{data/frozen\\_stage\\_probs.json}}) and never changes."
        )
    return (
        "\\begin{table}[!t]\n  \\centering\n"
        "  \\caption{Simulated tournament probabilities, top eight teams "
        "(live edition)}\\label{tab:champ}\n"
        "  \\begin{footnotesize}\n  \\begin{threeparttable}\n"
        f"    {{\\begin{{tabular*}}{{\\textwidth}}"
        f"{{@{{\\extracolsep{{\\fill}}}} {col_spec}}}\n"
        "      \\toprule\n"
        f"{header}\n"
        "      \\midrule\n"
        + "\n".join(rows) + "\n"
        "      \\bottomrule\n    \\end{tabular*}}\n"
        "    \\begin{tablenotes}\\notesize\n"
        f"      \\item \\textit{{Notes}}: {note}\n"
        "    \\end{tablenotes}\n  \\end{threeparttable}\n  \\end{footnotesize}\n"
        "\\end{table}"
    )


def trajfig(entries, live_fig=True):
    """Realized-trajectory figure once real results exist; demo until then."""
    if not entries or not live_fig:
        return (
            "\\begin{figure}[!t]\n"
            "  \\caption{Forecast evolution dress rehearsal}\\label{fig:trajectory}\n"
            "  \\begin{threeparttable}\n    {\\centering\n"
            "      \\includegraphics[width=0.94\\textwidth]{figs/fig_trajectory_demo.pdf}\\par}\n"
            "    \\begin{tablenotes}\\notesize\n"
            "      \\item \\textit{Notes}: Illustrative dress rehearsal on one simulated "
            "tournament (not the real forecast). The same figure is regenerated on real "
            "results after each match.\n"
            "    \\end{tablenotes}\n  \\end{threeparttable}\n\\end{figure}")
    n = len(entries)
    return (
        "\\begin{figure}[!t]\n"
        "  \\caption{Forecast evolution: the realized trajectory}\\label{fig:trajectory}\n"
        "  \\begin{threeparttable}\n    {\\centering\n"
        "      \\includegraphics[width=0.94\\textwidth]{figs/fig_trajectory_live.pdf}\\par}\n"
        "    \\begin{tablenotes}\\notesize\n"
        f"      \\item \\textit{{Notes}}: The live study on real results, through "
        f"{n} of 104 matches. Upper panel: each contender's champion probability after "
        "every recorded result, starting from the pre-tournament baseline. Lower panel: "
        "the information content of each result in bits (Equation~\\ref{eq:kl}). The "
        "figure is regenerated after every match; the dress-rehearsal version of this "
        "instrument, validated on a simulated tournament, is retained in the locked "
        "pre-kickoff edition.\n"
        "    \\end{tablenotes}\n  \\end{threeparttable}\n\\end{figure}")
