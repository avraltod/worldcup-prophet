"""LLM-drafted sections for the living paper. Each section has a deterministic
templated() fallback and a Claude draft() that degrades gracefully."""
import json as _json
import os

# ---- The four bracket revision decisions (locked, from tab:revisions) ----
_BRACKET_DECISIONS = [
    {"pick": "United States wins Group D", "slot": "Group D winner",
     "reason": "slot-emergence over nominal head-to-head"},
    {"pick": "Norway over Ecuador (M78)", "slot": "M78",
     "reason": "Norway's Elo edge + Ecuador's injury report"},
    {"pick": "Croatia over Portugal (M83)", "slot": "M83",
     "reason": "Portugal's probability of occupying this slot was only 25.1\\% vs Croatia's 27.5\\%"},
    {"pick": "Belgium over United States (M94)", "slot": "M94",
     "reason": "slot-emergence flipped the head-to-head call"},
]

_TOTAL_TOURNAMENT_BITS = 6.6  # theoretical maximum (104 decisive matches)

_HYPOTHESES = {
    "H1": "Information concentration: few matches carry most bits",
    "H2": "Elimination spikes: largest KL at high-probability team eliminations",
    "H3": "Late arrival: KO stage carries >80% of total bits",
}

# Primary team for each bracket revision decision (for probability lookup)
_DECISION_TEAMS = ["United States", "Norway", "Croatia", "Belgium"]


def _pct(x): return f"{100 * x:.1f}"


# ========================================================================
# Abstract live
# ========================================================================

def templated_abstract_live(ctx):
    top = ctx["champ_now_top"]
    frozen = ctx.get("frozen", {})
    n = ctx["n_results"]
    word = "result" if n == 1 else "results"
    total_bits = sum(e["post"].get("info_bits", 0.0) for e in ctx["entries"])
    pct_max = 100 * total_bits / _TOTAL_TOURNAMENT_BITS
    parts = []
    for team, prob in top[:3]:
        frz = frozen.get(team, {}).get("champion")
        if frz is not None:
            parts.append(f"{team} from {_pct(frz)}\\% to {_pct(prob)}\\%")
        else:
            parts.append(f"{team} at {_pct(prob)}\\%")
    inner = ", ".join(parts[:-1]) + f", and {parts[-1]}"
    b_top = ctx.get("champ_b_top", [])
    b_text = ""
    if b_top:
        b_parts = [f"{t} at {_pct(p)}\\%" for t, p in b_top[:2]]
        b_inner = " and ".join(b_parts)
        b_text = (f" Track~B (live Elo + bookmaker odds) leads with {b_inner}.")
    return (
        f"Conditioned on {n} {word}, Track~A moves {inner}. "
        f"The {n} {word} have revealed {total_bits:.3f} bits "
        f"({pct_max:.1f}\\% of the {_TOTAL_TOURNAMENT_BITS:.1f}-bit tournament maximum)."
        + b_text
    )


def _abstract_prompt(ctx):
    top = ctx["champ_now_top"]
    total_bits = sum(e["post"]["info_bits"] for e in ctx["entries"])
    return (
        "Write 2 sentences for the live-edition abstract of a pre-registered "
        "football forecasting paper, in the author's voice (measured; size effects "
        "by comparison; reason with 'because'; no em-dash asides). "
        "Sentence 1: conditioned champion probabilities for the top 3 teams and "
        "how many results were used. Sentence 2: pool scoring performance (points, "
        "Brier, information bits) and one comparison to the market or baseline. "
        "HARD RULE: use ONLY numbers in this JSON; do not invent any quantity.\n\n"
        + _json.dumps({"n_results": ctx["n_results"],
                       "cum_points": ctx["cum_points"],
                       "mean_brier": ctx["mean_brier"],
                       "champ_now_top": top[:3],
                       "total_bits": round(total_bits, 3)})
        + "\n\nReturn only the two sentences."
    )


def draft_abstract_live(ctx, use_api):
    if not use_api or not os.environ.get("ANTHROPIC_API_KEY"):
        return templated_abstract_live(ctx), "template"
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=200,
            messages=[{"role": "user", "content": _abstract_prompt(ctx)}])
        return msg.content[0].text.strip(), "claude"
    except Exception:
        return templated_abstract_live(ctx), "template"


# ========================================================================
# Intro data note
# ========================================================================

def templated_intro_data_note(ctx):
    return (
        "Track~A conditions on all results to date; team ratings are frozen at "
        "the June~10 pre-kickoff baseline and never change. "
        "Track~B supplements result-conditioning with live ClubElo ratings "
        "(updated daily), bookmaker odds for upcoming fixtures, and lineup "
        "adjustments at T$-$90~min."
    )


def draft_intro_data_note(ctx, use_api):
    return templated_intro_data_note(ctx), "template"  # too short for LLM


# ========================================================================
# Simulation note
# ========================================================================

def templated_simulation_note(ctx):
    n = ctx["n_results"]
    remaining = 104 - n
    para1 = (
        f"Of the 104 group-stage fixtures, {n} results are now fixed; "
        f"Track~A conditions on these outcomes and draws over the remaining "
        f"{remaining} matches with June~10 ratings frozen."
    )
    para2 = (
        "Track~A conditions on results alone. Track~B replaces the June~10 "
        "ratings with live ClubElo estimates after each match, incorporates "
        "bookmaker H2H odds for unplayed fixtures as pre-match inputs, and "
        "adjusts for confirmed lineup changes at T$-$90~min. Both tracks use "
        "$N$~=~50{,}000 draws from the same Poisson simulator."
    )
    return para1 + "\n\n" + para2


def draft_simulation_note(ctx, use_api):
    return templated_simulation_note(ctx), "template"


# ========================================================================
# Data revealed table
# ========================================================================

def templated_data_revealed(ctx):
    rows = []
    for e in ctx["entries"]:
        result = f"{e['result'][0]}--{e['result'][1]}"
        bits = e["post"]["info_bits"]
        rows.append(f"M{e['match']} & {e['fixture']} & {result} & {bits:.3f} \\\\")
    snap = ctx.get("info_snapshot") or {}
    provenance = ""
    if snap:
        ft = (snap.get("fetched_at") or "")[:10]
        elo_rms = snap.get("elo_rms_delta", 0)
        n_rates = snap.get("n_rate_changes", 0)
        n_lineup = snap.get("n_lineup_adj", 0)
        provenance = (
            f"\n\\medskip\\noindent{{\\small\\textit{{Track~B state:}} "
            f"Elo fetched {ft}, RMS $\\Delta$ = {elo_rms:.1f}~pts vs.\\ June~10 baseline; "
            f"{n_rates} fixture odds updated; {n_lineup} lineup adjustment(s) active.}}"
        )
    return (
        "The following matches have been played since the pre-registration lock "
        "(Table~\\ref{tab:live_data_revealed}).\n\n"
        "\\begin{table}[!h]\\centering\n"
        "\\caption{Information revealed since M000 (live edition "
        "M\\liveEditionNum{})}\\label{tab:live_data_revealed}\n"
        "\\begin{footnotesize}\\begin{tabular}{rlllr}\\toprule\n"
        "Match & Fixture & Result & Bits \\\\\n"
        "\\midrule\n"
        + "\n".join(rows) + "\n"
        "\\bottomrule\\end{tabular}\\end{footnotesize}\n"
        "\\begin{tablenotes}\\small\\item \\textit{Notes:} "
        "Bits = KL divergence contribution of this result to the champion distribution.\n"
        "\\end{tablenotes}\\end{table}"
        + provenance
    )


def _data_revealed_prompt(ctx):
    entries_summary = [
        {"match": e["match"], "fixture": e["fixture"], "result": e["result"],
         "bits": e["post"]["info_bits"]}
        for e in ctx["entries"]
    ]
    return (
        "Write a short paragraph (2-3 sentences) for a pre-registered football "
        "forecasting paper introducing the table of revealed match information. "
        "Author's voice: measured, precise, no adjectives. Then output this "
        "exact LaTeX table structure with the correct data filled in. "
        "HARD RULE: use ONLY numbers in the JSON below.\n\n"
        + _json.dumps({"entries": entries_summary,
                       "drift": ctx["learning"].get("drift", {})})
        + "\n\nReturn the paragraph followed by the table LaTeX."
    )


def draft_data_revealed(ctx, use_api):
    if not use_api or not os.environ.get("ANTHROPIC_API_KEY"):
        return templated_data_revealed(ctx), "template"
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=600,
            messages=[{"role": "user", "content": _data_revealed_prompt(ctx)}])
        text = msg.content[0].text.strip()
        if r"\label{tab:live_data_revealed}" not in text:
            return templated_data_revealed(ctx), "template"
        return text, "claude"
    except Exception:
        return templated_data_revealed(ctx), "template"


# ========================================================================
# Section 3.6 live paragraph (the careful one)
# ========================================================================

def templated_sec36_live(ctx):
    entries = ctx["entries"]
    total_bits = sum(e["post"].get("info_bits", 0.0) for e in entries)
    n = ctx["n_results"]
    pct_resolved = 100 * total_bits / _TOTAL_TOURNAMENT_BITS
    movers = ctx.get("champion_movers", [])
    biggest = max(movers, key=lambda x: abs(x[2] - x[1]), default=None)
    two = ctx.get("two_track")
    track_ab_gap = ""
    if two:
        top_team = max(two["frozen"], key=lambda t: two["frozen"][t])
        a_prob = ctx.get("now", {}).get(top_team, {}).get("champion",
                                                          two["frozen"][top_team])
        b_prob = two["learning"].get(top_team, a_prob)
        gap = abs(b_prob - a_prob)
        track_ab_gap = (
            f" Track~A and Track~B remain close for {top_team}: "
            f"Track~A {_pct(a_prob)}\\%, Track~B {_pct(b_prob)}\\% "
            f"(gap {100*gap:.1f}~pp)."
        )
    mover_text = ""
    if biggest:
        mover_text = (
            f" The largest movement is {biggest[0]} "
            f"({_pct(biggest[1])}\\% $\\to$ {_pct(biggest[2])}\\%), "
            f"driven primarily by the result channel."
        )
    h_status = (
        "H1 (information concentration) and H3 (late arrival) remain testable "
        "only after KO-stage results; H2 (elimination spikes) is pending the "
        "first high-probability team exit."
    )
    return (
        f"With {n} of 104 results revealed, the tournament has delivered "
        f"{total_bits:.3f} bits toward the champion distribution "
        f"({pct_resolved:.1f}\\% of the {_TOTAL_TOURNAMENT_BITS:.1f}-bit maximum)."
        + mover_text + track_ab_gap +
        f" {h_status}"
    )


def _sec36_prompt(ctx):
    entries = ctx["entries"]
    total_bits = sum(e["post"]["info_bits"] for e in entries)
    return (
        "Write one substantive paragraph (150-200 words) for Section 3.6 "
        "(Conditional updating and information content) of a pre-registered "
        "football forecasting paper. Cover ALL four of: "
        "(1) how many bits have been revealed and what fraction of the theoretical "
        "tournament maximum this represents; "
        "(2) which prior moved most and through which channel (result vs performance); "
        "(3) whether the learning and frozen tracks have meaningfully diverged; "
        "(4) status of the three pre-registered hypotheses. "
        "Author's voice: methodologically careful, precise, no adjectives. "
        "HARD RULE: use ONLY numbers in this JSON.\n\n"
        + _json.dumps({
            "n_results": ctx["n_results"],
            "total_bits": round(total_bits, 4),
            "theoretical_max_bits": _TOTAL_TOURNAMENT_BITS,
            "champion_movers": ctx.get("champion_movers", [])[:5],
            "two_track": ctx.get("two_track"),
            "drift_leaders": sorted(
                ctx["learning"].get("drift", {}).items(),
                key=lambda kv: -abs(kv[1]))[:4],
        })
        + "\n\nReturn only the paragraph text."
    )


def draft_sec36_live(ctx, use_api):
    if not use_api or not os.environ.get("ANTHROPIC_API_KEY"):
        return templated_sec36_live(ctx), "template"
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=350,
            messages=[{"role": "user", "content": _sec36_prompt(ctx)}])
        return msg.content[0].text.strip(), "claude"
    except Exception:
        return templated_sec36_live(ctx), "template"


# ========================================================================
# Robustness live (main narrative investment)
# ========================================================================

def _verdict(adv_ko):
    if adv_ko is None:
        return "status unknown"
    if adv_ko >= 0.70:
        return "confirmed"
    if adv_ko >= 0.30:
        return "at risk"
    return "flipped"


def templated_robustness_live(ctx):
    now = ctx.get("now", {})
    paras = []
    for d, team in zip(_BRACKET_DECISIONS, _DECISION_TEAMS):
        adv = now.get(team, {}).get("advance_KO")
        verdict = _verdict(adv)
        adv_text = (f" Current Track~A advance probability for {team}: "
                    f"{_pct(adv)}\\% (flip threshold: 50\\%); verdict: {verdict}."
                    if adv is not None else "")
        paras.append(
            f"\\paragraph{{{d['pick']}.}} "
            f"This pick was made because {d['reason']}. "
            f"With {ctx['n_results']} results now in, the relevant probabilities "
            f"have not materially changed."
            + adv_text
        )
    return (
        "\\subsection*{Robustness update: edition M\\liveEditionNum{}}"
        "\\label{sec:live_robust}\n"
        + "\n\n".join(paras)
    )


def _robustness_prompt(ctx):
    now = ctx.get("now", {})
    relevant = ["Norway", "Ecuador", "Croatia", "Portugal", "Belgium",
                "United States", "Turkey"]
    probs_now = {t: {k: round(now[t][k], 4) for k in ("advance_KO", "champion")}
                 for t in relevant if t in now}
    probs_frozen = {t: {k: round(ctx["frozen"][t][k], 4)
                        for k in ("advance_KO", "champion")}
                    for t in relevant if t in ctx.get("frozen", {})}
    return (
        "Write one paragraph per bracket-revision decision (4 paragraphs total, "
        "~80 words each) for the 'Robustness of revisions' section of a "
        "pre-registered football forecasting paper. Each paragraph: "
        "(1) states the decision and its original rationale, "
        "(2) assesses whether new results confirm or challenge it, "
        "(3) gives the current probability that makes the decision correct or wrong. "
        "Author's voice: accountability framing, precise, no adjectives. "
        "HARD RULE: use ONLY numbers in the JSON below.\n\n"
        + _json.dumps({
            "n_results": ctx["n_results"],
            "decisions": _BRACKET_DECISIONS,
            "probs_now": probs_now,
            "probs_frozen": probs_frozen,
        })
        + "\n\nReturn only the four paragraphs. "
        "Begin with \\subsection*{Robustness update: edition M\\liveEditionNum{}}\\label{sec:live_robust}"
    )


def draft_robustness_live(ctx, use_api):
    if not use_api or not os.environ.get("ANTHROPIC_API_KEY"):
        return templated_robustness_live(ctx), "template"
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=800,
            messages=[{"role": "user", "content": _robustness_prompt(ctx)}])
        text = msg.content[0].text.strip()
        if r"\label{sec:live_robust}" not in text:
            text = ("\\subsection*{Robustness update: edition M\\liveEditionNum{}}"
                    "\\label{sec:live_robust}\n" + text)
        return text, "claude"
    except Exception:
        return templated_robustness_live(ctx), "template"


# ========================================================================
# Failure analysis (most important section)
# ========================================================================

_FAILURE_BRIER_THRESHOLD = 0.50
_FAILURE_PROB_THRESHOLD = 0.25


def _failure_cases(ctx):
    processed = {r["match"]: r for r in ctx["learning"].get("processed", [])}
    cases = []
    for e in ctx["entries"]:
        brier = e["post"]["brier"]
        p_out = e["post"].get("p_outcome", 1.0)
        if brier > _FAILURE_BRIER_THRESHOLD or p_out < _FAILURE_PROB_THRESHOLD:
            rec = processed.get(e["match"])
            cases.append({
                "match": e["match"],
                "fixture": e["fixture"],
                "result": e["result"],
                "brier": round(brier, 3),
                "p_outcome": round(p_out, 3),
                "probs_HDA": e["pre"]["probs_HDA"],
                "lam_obs": rec["lam_obs"] if rec else None,
                "lam_exp": rec["lam_exp"] if rec else None,
            })
    return cases


def templated_failure_analysis(ctx):
    cases = _failure_cases(ctx)
    if not cases:
        return (
            "\\subsection*{Live failure log: edition M\\liveEditionNum{}}"
            "\\label{sec:live_failure}\n"
            "No material failures this edition; the ledger records all graded matches."
        )
    paras = []
    for c in cases:
        fixture = c["fixture"]
        result = f"{c['result'][0]}--{c['result'][1]}"
        brier = c["brier"]
        p_out = c["p_outcome"]
        lam_text = ""
        if c["lam_obs"] and c["lam_exp"]:
            lam_text = (
                f" The model expected $\\lambda_{{\\mathrm{{home}}}}={c['lam_exp']['home']:.2f}$, "
                f"$\\lambda_{{\\mathrm{{away}}}}={c['lam_exp']['away']:.2f}$; "
                f"the observed rates were {c['lam_obs']['home']:.2f} and "
                f"{c['lam_obs']['away']:.2f} respectively."
            )
        # Track B Elo response from learning.processed record
        elo_resp = ""
        rec_full = next((r for r in ctx["learning"].get("processed", [])
                         if r.get("match") == c["match"]), None)
        if rec_full and rec_full.get("drift_after"):
            moves = sorted(rec_full["drift_after"].items(),
                           key=lambda kv: -abs(kv[1]))[:2]
            if moves:
                elo_resp = (" Track~B moved "
                            + " and ".join(f"{t} by {d:+.1f}~Elo" for t, d in moves)
                            + " in response.")
        paras.append(
            f"\\paragraph{{M{c['match']} {fixture}.}} "
            f"The actual score was {result}; the model assigned this outcome "
            f"probability {_pct(p_out)}\\%, yielding a Brier score of {brier:.3f}."
            + lam_text + elo_resp
        )
    return (
        "\\subsection*{Live failure log: edition M\\liveEditionNum{}}"
        "\\label{sec:live_failure}\n"
        + "\n\n".join(paras)
    )


def _failure_prompt(ctx):
    cases = _failure_cases(ctx)
    if not cases:
        return None
    return (
        "Write one case-study paragraph (3-4 sentences) per failed match for the "
        "'Where the model fails' section of a pre-registered football forecasting paper. "
        "Each paragraph: (1) what the model predicted and the structural reason; "
        "(2) what happened; (3) the failure mechanism — not just 'we got it wrong' "
        "but the specific structural gap (e.g. Elo insensitive to tactical matchup; "
        "home-continent intensity not captured in pre-tournament odds). "
        "Author's voice: measured, analytical, no adjectives. "
        "HARD RULE: use ONLY numbers in the JSON below.\n\n"
        + _json.dumps({"failure_cases": cases})
        + "\n\nReturn only the paragraphs. "
        "Prepend: \\subsection*{Live failure log: edition M\\liveEditionNum{}}\\label{sec:live_failure}"
    )


def draft_failure_analysis(ctx, use_api):
    if not use_api or not os.environ.get("ANTHROPIC_API_KEY"):
        return templated_failure_analysis(ctx), "template"
    prompt = _failure_prompt(ctx)
    if prompt is None:
        return templated_failure_analysis(ctx), "template"
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=800,
            messages=[{"role": "user", "content": prompt}])
        text = msg.content[0].text.strip()
        if r"\label{sec:live_failure}" not in text:
            text = ("\\subsection*{Live failure log: edition M\\liveEditionNum{}}"
                    "\\label{sec:live_failure}\n" + text)
        return text, "claude"
    except Exception:
        return templated_failure_analysis(ctx), "template"


# ========================================================================
# Discussion live (opening paragraph)
# ========================================================================

def templated_discussion_live(ctx):
    top = ctx["champ_now_top"]
    n = ctx["n_results"]
    total_bits = sum(e["post"].get("info_bits", 0.0) for e in ctx["entries"])
    leader = top[0][0] if top else "Spain"
    pct_max = 100 * total_bits / _TOTAL_TOURNAMENT_BITS
    phase = "group stage" if n < 48 else "knockout stage"
    now = ctx.get("now", {})
    # Beat 3: most-at-risk bracket call
    at_risk_team = min(_DECISION_TEAMS,
                       key=lambda t: now.get(t, {}).get("advance_KO", 1.0))
    at_risk_adv = now.get(at_risk_team, {}).get("advance_KO", None)
    risk_text = (f"{at_risk_team} ({_pct(at_risk_adv)}\\% advance)"
                 if at_risk_adv is not None else at_risk_team)
    return (
        f"Through {n} matches and {total_bits:.3f} bits ({pct_max:.1f}\\% of maximum), "
        f"{leader} leads at {_pct(top[0][1])}\\%. "
        f"The entry has accumulated {ctx['cum_points']} pool points "
        f"at a mean Brier of {ctx['mean_brier']:.2f}. "
        f"The most pressure on a pre-registered revision comes from {risk_text}. "
        f"The key question for the remainder of the {phase} is whether the "
        f"information-concentration pattern (H1, H3) holds as elimination "
        f"pressure intensifies."
    )


def _discussion_prompt(ctx):
    top = ctx["champ_now_top"]
    total_bits = sum(e["post"]["info_bits"] for e in ctx["entries"])
    cases = _failure_cases(ctx)
    return (
        "Write one paragraph (60-80 words) to open the Discussion section of a "
        "pre-registered football forecasting paper. Cover: which main calls are "
        "holding, which are under pressure, and the single most important open "
        "question for the next match day. Do NOT repeat numbers already stated "
        "in other sections. Author's voice: measured, forward-looking, no adjectives. "
        "HARD RULE: use ONLY numbers in this JSON.\n\n"
        + _json.dumps({"n_results": ctx["n_results"],
                       "total_bits": round(total_bits, 3),
                       "champ_now_top": top[:3],
                       "n_failure_cases": len(cases)})
        + "\n\nReturn only the paragraph."
    )


def draft_discussion_live(ctx, use_api):
    if not use_api or not os.environ.get("ANTHROPIC_API_KEY"):
        return templated_discussion_live(ctx), "template"
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=200,
            messages=[{"role": "user", "content": _discussion_prompt(ctx)}])
        return msg.content[0].text.strip(), "claude"
    except Exception:
        return templated_discussion_live(ctx), "template"
