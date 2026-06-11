"""Draft the per-match interpretation. templated() is a pure, deterministic
fallback that always works (no secrets). draft() prefers Claude when use_api and
a key are available, and degrades to templated() on any failure so the hands-off
pipeline never stalls."""
import os


def templated(e):
    pts = e["post"]["points"]
    bits = e["post"]["info_bits"]
    ph, pd, pa = e["pre"]["probs_HDA"]
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
