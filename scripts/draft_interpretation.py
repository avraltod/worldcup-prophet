"""Draft the per-match interpretation. templated() is a pure, deterministic
fallback that always works (no secrets). draft() prefers Claude when use_api and
a key are available, and degrades to templated() on any failure so the hands-off
pipeline never stalls."""
import os


def templated(e):
    pts = e["post"]["points"]
    bits = e["post"]["info_bits"]
    res = e["result"]
    outcome = "home win" if res[0] > res[1] else ("draw" if res[0] == res[1] else "away win")
    moved = "barely moved the forecast" if bits < 0.05 else "moved the forecast materially"
    p_real = e["post"]["p_outcome"]
    return (f"A {round(p_real * 100)}%-likely {outcome} arrived; the result {moved} "
            f"({bits:.3f} bits), and the pick scored {pts} of 3.")


def draft(e, corrections, use_api):
    if not use_api or not os.environ.get("ANTHROPIC_API_KEY"):
        return templated(e), "template"
    try:
        import anthropic
        client = anthropic.Anthropic()
        prompt = _build_prompt(e, corrections)
        msg = client.messages.create(
            model="claude-opus-4-8", max_tokens=220,
            messages=[{"role": "user", "content": prompt}])
        text = msg.content[0].text.strip()
        return text, "claude"
    except Exception:
        return templated(e), "template"


def _build_prompt(e, corrections):
    return (
        "Write 1-3 sentences of contemporaneous interpretation of this World Cup "
        "match result for a pre-registered forecasting paper, in the author's voice "
        "(measured; the data is the subject of a finding; size effects by comparison, "
        "not adjectives; reason with 'because'; no em-dash asides). "
        "Do NOT change any numbers; report them as given.\n\n"
        f"Fixture: {e['fixture']}\nResult: {e['result']}\n"
        f"Pick: {e['pre']['pick']} (P[H/D/A]={e['pre']['probs_HDA']})\n"
        f"Points: {e['post']['points']}/3  Brier: {e['post']['brier']}  "
        f"info_bits: {e['post']['info_bits']}\n\n"
        + (f"Prior accepted notes (match the style):\n{corrections}\n" if corrections else "")
        + "Return only the interpretation text."
    )


def templated_revision(pack):
    """Deterministic 'changes since the previous edition' paragraph."""
    moved = ", ".join(f"{t} {100 * (b - a):+.1f} pp" for t, a, b in pack["champ_deltas"])
    perf = ""
    if pack.get("lam_obs") and pack.get("lam_exp"):
        perf = (f" Performance signal (home/away): observed "
                f"{pack['lam_obs']['home']:.2f}/{pack['lam_obs']['away']:.2f} "
                f"expected goals against "
                f"{pack['lam_exp']['home']:.2f}/{pack['lam_exp']['away']:.2f} "
                f"expected.")
    return (f"Edition M{pack['edition']:03d} conditions on {pack['fixture']} "
            f"{pack['result'][0]}--{pack['result'][1]} "
            f"({pack['points']} of 3 points, {pack['info_bits']:.3f} bits)."
            f"{(' Champion movement: ' + moved + '.') if moved else ''}{perf}")


def draft_revision(pack, corrections, use_api):
    """Claude-drafted revision narrative grounded ONLY in the pack's numbers;
    deterministic fallback so an edition never blocks."""
    if not use_api or not os.environ.get("ANTHROPIC_API_KEY"):
        return templated_revision(pack), "template"
    try:
        import json as _json
        import anthropic
        client = anthropic.Anthropic()
        prompt = (
            "Write 2-4 sentences for the 'Revision report' section of a "
            "pre-registered live-forecasting paper: what this match changed in "
            "the forecast and why, in the author's voice (measured; size effects "
            "by comparison, not adjectives; reason with 'because'; no em-dash "
            "asides). HARD RULE: use ONLY numbers present in the JSON below; do "
            "not invent or recompute any quantity.\n\n"
            + _json.dumps(pack, ensure_ascii=False)
            + ("\n\nPrior accepted notes (match the style):\n" + corrections
               if corrections else "")
            + "\n\nReturn only the narrative text.")
        msg = client.messages.create(
            model="claude-opus-4-8", max_tokens=400,
            messages=[{"role": "user", "content": prompt}])
        return msg.content[0].text.strip(), "claude"
    except Exception:
        return templated_revision(pack), "template"
