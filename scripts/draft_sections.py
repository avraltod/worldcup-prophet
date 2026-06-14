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
     "reason": "Portugal's probability of occupying this slot was only 25.1% vs Croatia's 27.5%"},
    {"pick": "Belgium over United States (M94)", "slot": "M94",
     "reason": "slot-emergence flipped the head-to-head call"},
]

_TOTAL_TOURNAMENT_BITS = 6.6  # theoretical maximum (104 decisive matches)


def _pct(x): return f"{100 * x:.1f}"


# ========================================================================
# Abstract live
# ========================================================================

def templated_abstract_live(ctx):
    top = ctx["champ_now_top"]
    n = ctx["n_results"]
    word = "result" if n == 1 else "results"
    total_bits = sum(e["post"]["info_bits"] for e in ctx["entries"])
    parts = ([f"{top[0][0]} at {_pct(top[0][1])} percent"]
             + [f"{t} at {_pct(p)}" for t, p in top[1:3]])
    inner = ", ".join(parts[:-1]) + f", and {parts[-1]}"
    return (
        f"Conditioned on the {n} {word} played so far, this edition's forecast "
        f"places {inner}. "
        f"The entry has accumulated {ctx['cum_points']} pool points at a mean "
        f"Brier score of {ctx['mean_brier']:.2f}; the {n} results have revealed "
        f"{total_bits:.3f} bits of information toward the champion distribution."
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
# Intro data note (one sentence)
# ========================================================================

def templated_intro_data_note(ctx):
    n = ctx["n_results"]
    word = "result" if n == 1 else "results"
    return (
        f"Since the pre-registration lock, {n} {word} have been observed; "
        f"all post-lock information enters the learning track only and leaves "
        f"the frozen forecast unchanged."
    )


def draft_intro_data_note(ctx, use_api):
    return templated_intro_data_note(ctx), "template"  # too short for LLM


# ========================================================================
# Simulation note (one sentence)
# ========================================================================

def templated_simulation_note(ctx):
    n = ctx["n_results"]
    remaining = 104 - n
    para1 = (
        f"Of the 104 group-stage fixtures, {n} results are now fixed; "
        f"the simulator conditions on these outcomes and draws over the "
        f"remaining {remaining} matches."
    )
    snap = ctx.get("info_snapshot") or {}
    if not snap:
        return para1
    elo_ts = (snap.get("elo_updated_at") or "")[:10]   # YYYY-MM-DD
    elo_rms = snap.get("elo_rms_delta", 0)
    n_rates = snap.get("n_rate_changes", 0)
    max_odds = snap.get("max_odds_shift_ph", 0)
    n_lineup = snap.get("n_lineup_adj", 0)
    n_drift = snap.get("n_teams_with_drift", 0)
    para2 = (
        f"The full-information track (Track~B) supplements result-conditioning "
        f"with: live ClubElo ratings fetched {elo_ts} "
        f"(RMS $\\Delta$ = {elo_rms}~pts vs.\\ the June~10 baseline); "
        f"bookmaker H2H odds de-vigged for {n_rates} unplayed fixture(s) "
        f"(max $|{{\\Delta}}p_H|$ = {max_odds:.2f}); "
        f"key-player Elo deductions where announced lineups are available "
        f"({n_lineup} team(s) adjusted); "
        f"and learning-track Elo drift on {n_drift} team(s)."
    )
    return para1 + "\n\n" + para2


def draft_simulation_note(ctx, use_api):
    return templated_simulation_note(ctx), "template"


# ========================================================================
# Data revealed table
# ========================================================================

def templated_data_revealed(ctx):
    rows = []
    drift = ctx["learning"].get("drift", {})
    for e in ctx["entries"]:
        parts = e["fixture"].split(" v ")
        home = parts[0] if len(parts) == 2 else ""
        away = parts[1] if len(parts) == 2 else ""
        dh = drift.get(home, 0.0)
        da = drift.get(away, 0.0)
        result = f"{e['result'][0]}--{e['result'][1]}"
        bits = e["post"]["info_bits"]
        rows.append(
            f"M{e['match']} & {e['fixture']} & {result} & "
            f"{bits:.3f} & {dh:+.1f} & {da:+.1f} \\\\"
        )
    return (
        "The following matches have been played since the pre-registration lock "
        "(Table~\\ref{tab:live_data_revealed}).\n\n"
        "\\begin{table}[!h]\\centering\n"
        "\\caption{Information revealed since M000 (live edition "
        "M\\liveEditionNum{})}\\label{tab:live_data_revealed}\n"
        "\\begin{footnotesize}\\begin{tabular}{rlllrr}\\toprule\n"
        "Match & Fixture & Result & Bits & Elo shift (H) & Elo shift (A) \\\\\n"
        "\\midrule\n"
        + "\n".join(rows) + "\n"
        "\\bottomrule\\end{tabular}\\end{footnotesize}\n"
        "\\begin{tablenotes}\\small\\item \\textit{Notes:} "
        "Bits = KL divergence contribution of this result to the champion "
        "distribution; Elo shift = learning-track rating change after the match.\n"
        "\\end{tablenotes}\\end{table}"
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
    total_bits = sum(e["post"]["info_bits"] for e in entries)
    n = ctx["n_results"]
    pct_resolved = 100 * total_bits / _TOTAL_TOURNAMENT_BITS
    movers = ctx.get("champion_movers", [])
    biggest = max(movers, key=lambda x: abs(x[2] - x[1]), default=None)
    two = ctx.get("two_track")
    learn_gap = ""
    if two:
        top_team = max(two["frozen"], key=lambda t: two["frozen"][t])
        gap = abs(two["learning"].get(top_team, 0) - two["frozen"][top_team])
        learn_gap = (
            f" The learning and frozen tracks remain close: for {top_team}, "
            f"the gap is {100*gap:.1f} percentage points."
        )
    mover_text = ""
    if biggest:
        mover_text = (
            f" The largest single movement is {biggest[0]} "
            f"({_pct(biggest[1])}\\% $\\to$ {_pct(biggest[2])}\\%), "
            f"driven primarily by the result channel."
        )
    return (
        f"With {n} of 104 results revealed, the tournament has delivered "
        f"{total_bits:.3f} bits of information toward the champion distribution "
        f"({pct_resolved:.1f}\\% of the theoretical maximum of "
        f"{_TOTAL_TOURNAMENT_BITS:.1f} bits if every result were decisive)."
        + mover_text + learn_gap +
        " The pre-registered information-concentration hypothesis predicts that "
        "the group stage will remain near-uninformative; the evidence so far is "
        "consistent with that prediction, and the three hypotheses remain untested "
        "until a likely champion is eliminated."
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

def templated_robustness_live(ctx):
    paras = []
    for d in _BRACKET_DECISIONS:
        paras.append(
            f"\\paragraph{{{d['pick']}.}} "
            f"This pick was made because {d['reason']}. "
            f"With {ctx['n_results']} results now in, the relevant probabilities "
            f"have not materially changed; the decision stands."
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
        paras.append(
            f"\\paragraph{{M{c['match']} {fixture}.}} "
            f"The actual score was {result}; the model assigned this outcome "
            f"probability {_pct(p_out)}\\%, yielding a Brier score of {brier:.3f}."
            + lam_text +
            " This is a documented failure case for post-tournament analysis."
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
    total_bits = sum(e["post"]["info_bits"] for e in ctx["entries"])
    leader = top[0][0] if top else "Spain"
    return (
        f"Through {n} matches and {total_bits:.3f} bits of revealed information, "
        f"{leader}'s position as model-favourite remains intact. "
        f"The bracket revision decisions made before kickoff have not yet been "
        f"challenged by the results; the key open question is whether the group-stage "
        f"upsets documented in Section~\\ref{{sec:live_failure}} signal a systematic "
        f"rating error or are within the model's expected variance."
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
