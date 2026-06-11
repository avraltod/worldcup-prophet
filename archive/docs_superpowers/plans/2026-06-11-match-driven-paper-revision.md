# Match-Driven Paper Revision — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After each World Cup match, automatically revise the paper's live-study layer (a new versioned PDF per match, 104 in total) from the v2 before/after records — without ever touching the pre-registered forecast.

**Architecture:** A finished match's POST record in `data/trajectory_v2.json` triggers a driver (`update_after_match.py`) that builds a contemporaneous "Match Book" entry, drafts an interpretation (Claude in CI, deterministic template as fallback), regenerates marker-delimited LaTeX blocks plus a `live_stats.tex` macro file, appends a response-to-reviewer note, builds the PDF with latexmk, and snapshots it as a CI artifact. A separate, isolated GitHub Actions workflow runs the whole thing hands-off; the v2 recorder is untouched. An allowlist + frozen-hash guard make it impossible to modify the pre-registered layer.

**Tech Stack:** Python 3.12 (stdlib + `anthropic` SDK in CI only), LaTeX/latexmk, GitHub Actions, pytest.

**Spec:** `archive/docs_superpowers/specs/2026-06-11-match-driven-paper-revision-design.md`

---

## Data contracts (read first — used by every task)

These shapes are fixed across all tasks. Property names are authoritative.

**v2 records** (already produced, in `data/trajectory_v2.json`, a list):
```python
# PRE record
{"phase": "pre", "match": 1, "label": "PRE M1 Mexico v South Africa",
 "time": "2026-06-11T17:58:51Z", "kickoff": "2026-06-11T19:00:00Z", "n_recorded": 0,
 "champion": {"Spain": 0.2711, ...}, "market_champion": {"Spain": 0.164, ...},
 "info_bits": 0.0, "lineup": None, "result": None, "performance": None}
# POST record
{"phase": "post", "match": 1, "label": "POST M1 Mexico v South Africa",
 "time": "...", "kickoff": "...", "n_recorded": 1,
 "champion": {...}, "market_champion": {...}, "info_bits": 0.0011, "lineup": None,
 "result": [2, 0], "performance": {"points": 1, "ev_points": 0.855, "p_outcome": 0.6718, "brier": 0.1655}}
```

**`data/match_expectations.json`** (a list): each item
```python
{"match": 1, "row": 4, "group": "A", "home": "Mexico", "away": "South Africa",
 "pick": [2, 1], "p_exact": 0.0916, "p_outcome": 0.6718, "ev_points": 0.855,
 "lh": 1.9, "la": 0.65, "probs_HDA": [0.6718, 0.2087, 0.1193]}
```

**Entry** (the Match Book unit — a dict; this plan's canonical internal type):
```python
{"match": 1, "stage": "Group A", "fixture": "Mexico v South Africa",
 "kickoff": "2026-06-11T19:00:00Z", "documented_at": "2026-06-11T21:10:58Z",
 "forecast_commit": "b855bf2", "failure_mode": None,           # or a FAILURE_MODES key
 "pre": {"pick": [2, 1], "probs_HDA": [0.6718, 0.2087, 0.1193],
         "market_top": [["Spain", 0.164], ...], "champ_top": [["Spain", 0.2711], ...],
         "watch_line": "a South Africa draw or win would be the surprise (model 67% home)."},
 "result": [2, 0],
 "post": {"points": 1, "brier": 0.1655, "p_outcome": 0.6718, "info_bits": 0.0011,
          "movers": [["Argentina", 0.1768, 0.1815], ...]},
 "interpretation": "...", "interpretation_source": "template"}  # claude|template|human
```

**live_stats** (the consistency object):
```python
{"documented": 1, "cum_points": 1, "mean_brier": 0.1655, "exact_rate": 0.0,
 "re_ev_delta": 0, "champ_top": [["Spain", 0.2711], ...],
 "failure_tally": {"systematic_rating_error": 0, ...}}
```

**FAILURE_MODES** (keys, matching paper L541–546):
```python
FAILURE_MODES = ["champion_call", "bracket_decay", "group_upset_cascade",
                 "md3_rotation", "systematic_rating_error", "knockout_coinflip"]
```

**Paper marker pairs** (added in Task 5), inside `paper/Avraa_WC2026_paper.tex`:
```
% LIVE-EVOLUTION-TABLE:START ... % LIVE-EVOLUTION-TABLE:END
% LIVE-EVOLUTION-NARRATIVE:START ... % LIVE-EVOLUTION-NARRATIVE:END
```

---

## File structure

| File | Responsibility |
|---|---|
| `scripts/match_book.py` | Build an Entry from v2 records + expectations; serialize/parse `M0XX.md`; manage `index.json`. Pure. |
| `scripts/live_stats.py` | Compute the aggregate live_stats from Entries; render `live_stats.tex` macros. Pure. |
| `scripts/draft_interpretation.py` | Deterministic templated interpretation (pure) + Claude-API path with template fallback. |
| `scripts/render_evolution.py` | Build the ledger table + narrative LaTeX; guarded marker replacement; frozen-hash. Pure. |
| `scripts/update_after_match.py` | The driver: detect → build → draft → render → REVISIONS → latexmk → guard → commit. CLI. |
| `.github/workflows/paper-revision.yml` | Isolated CI: chains off live-update-v2; carries `ANTHROPIC_API_KEY`. |
| `paper/Avraa_WC2026_paper.tex` | Add marker blocks + `\input{live_stats}` + two tagged-twin macros. |
| `paper/live_stats.tex` | GENERATED macros (created by the pipeline). |
| `paper/REVISIONS.md` | GENERATED response-to-reviewer log. |
| `paper/match_book/` | `index.json`, `corrections.md`, `M0XX.md` entries. |
| `tests/test_match_book.py`, `test_live_stats.py`, `test_draft_interpretation.py`, `test_render_evolution.py`, `test_update_after_match.py` | Unit + integration tests. |

---

## Task 1: Match Book core (`match_book.py`)

**Files:**
- Create: `scripts/match_book.py`
- Test: `tests/test_match_book.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_match_book.py
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import match_book as mb

PRE = {"phase": "pre", "match": 1, "kickoff": "2026-06-11T19:00:00Z",
       "champion": {"Spain": 0.2711, "Argentina": 0.1768, "France": 0.1428,
                    "Portugal": 0.093, "England": 0.0698, "Brazil": 0.0359},
       "market_champion": {"Spain": 0.164, "France": 0.155, "Portugal": 0.106},
       "info_bits": 0.0, "result": None, "performance": None}
POST = {"phase": "post", "match": 1, "kickoff": "2026-06-11T19:00:00Z",
        "champion": {"Spain": 0.2711, "Argentina": 0.1815, "England": 0.0688},
        "info_bits": 0.0011, "result": [2, 0],
        "performance": {"points": 1, "ev_points": 0.855, "p_outcome": 0.6718, "brier": 0.1655}}
EXP = [{"match": 1, "group": "A", "home": "Mexico", "away": "South Africa",
        "pick": [2, 1], "probs_HDA": [0.6718, 0.2087, 0.1193], "lh": 1.9, "la": 0.65}]

def test_build_entry_fills_pre_and_post_from_records():
    e = mb.build_entry(1, [PRE, POST], EXP, forecast_commit="abc1234",
                       documented_at="2026-06-11T21:10:58Z")
    assert e["match"] == 1
    assert e["stage"] == "Group A"
    assert e["fixture"] == "Mexico v South Africa"
    assert e["result"] == [2, 0]
    assert e["pre"]["pick"] == [2, 1]
    assert e["pre"]["champ_top"][0] == ["Spain", 0.2711]
    assert e["post"]["points"] == 1
    assert e["post"]["brier"] == 0.1655
    # top movers: largest |after-before| among teams present in both champion dicts
    assert ["Argentina", 0.1768, 0.1815] in e["post"]["movers"]
    assert e["interpretation"] == ""
    assert e["forecast_commit"] == "abc1234"

def test_roundtrip_markdown():
    e = mb.build_entry(1, [PRE, POST], EXP, "abc1234", "2026-06-11T21:10:58Z")
    e["interpretation"] = "A likely home win arrived; the title race barely moved."
    e["interpretation_source"] = "human"
    e["failure_mode"] = None
    text = mb.to_markdown(e)
    back = mb.parse_markdown(text)
    assert back["match"] == 1
    assert back["interpretation"] == e["interpretation"]
    assert back["interpretation_source"] == "human"
    assert back["pre"]["pick"] == [2, 1]
    assert back["result"] == [2, 0]

def test_index_mark_and_query(tmp_path):
    idx = tmp_path / "index.json"
    assert mb.is_documented(idx, 1) is False
    mb.mark_documented(idx, 1)
    assert mb.is_documented(idx, 1) is True
    assert mb.documented_matches(idx) == [1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_match_book.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'match_book'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/match_book.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_match_book.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/match_book.py tests/test_match_book.py
git commit -m "Add Match Book core: build/serialize entries, index tracking"
```

---

## Task 2: Aggregate live_stats (`live_stats.py`)

**Files:**
- Create: `scripts/live_stats.py`
- Test: `tests/test_live_stats.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_live_stats.py
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import live_stats as ls

E1 = {"match": 1, "result": [2, 0], "failure_mode": None,
      "pre": {"pick": [2, 1]},
      "post": {"points": 1, "brier": 0.1655},
      "champ_top_full": {"Spain": 0.2711, "Argentina": 0.1815}}
E2 = {"match": 2, "result": [1, 1], "failure_mode": "systematic_rating_error",
      "pre": {"pick": [1, 1]},
      "post": {"points": 3, "brier": 0.40},
      "champ_top_full": {"Spain": 0.27, "Argentina": 0.18}}

def test_compute_aggregates():
    s = ls.compute([E1, E2], latest_champion={"Spain": 0.27, "Argentina": 0.18})
    assert s["documented"] == 2
    assert s["cum_points"] == 4
    assert round(s["mean_brier"], 4) == 0.2828      # (0.1655+0.40)/2
    assert round(s["exact_rate"], 4) == 0.5          # E2 pick == result
    assert s["failure_tally"]["systematic_rating_error"] == 1
    assert s["champ_top"][0] == ["Spain", 0.27]

def test_render_macros_are_consistent():
    s = ls.compute([E1, E2], latest_champion={"Spain": 0.27})
    tex = ls.render_macros(s)
    assert r"\def\liveCumPoints{4}" in tex
    assert r"\def\liveMeanBrier{0.28}" in tex
    assert r"\def\liveDocumented{2}" in tex
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_live_stats.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'live_stats'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/live_stats.py
"""Aggregate the documented Match Book entries into one live_stats object and
render it as LaTeX macros. This is the single source for every living number in
the paper, so no figure can drift out of sync. Pure."""
from match_book import FAILURE_MODES


def _exact(e):
    return list(e["pre"]["pick"]) == list(e["result"])


def compute(entries, latest_champion):
    n = len(entries)
    cum = sum(e["post"]["points"] for e in entries)
    mean_brier = sum(e["post"]["brier"] for e in entries) / n if n else 0.0
    exact = sum(1 for e in entries if _exact(e)) / n if n else 0.0
    tally = {k: 0 for k in FAILURE_MODES}
    for e in entries:
        if e["failure_mode"] in tally:
            tally[e["failure_mode"]] += 1
    champ_top = [[t, round(p, 4)] for t, p in
                 sorted(latest_champion.items(), key=lambda kv: -kv[1])[:5]]
    return {"documented": n, "cum_points": cum, "mean_brier": mean_brier,
            "exact_rate": exact, "re_ev_delta": 0, "champ_top": champ_top,
            "failure_tally": tally}


def render_macros(s):
    lines = [
        "% GENERATED by scripts/live_stats.py — do not edit by hand.",
        r"\def\liveDocumented{%d}" % s["documented"],
        r"\def\liveCumPoints{%d}" % s["cum_points"],
        r"\def\liveMeanBrier{%.2f}" % s["mean_brier"],
        r"\def\liveExactRate{%.2f}" % s["exact_rate"],
    ]
    return "\n".join(lines) + "\n"
```

> Note: `re_ev_delta` is wired in Task 6 (needs `ev321.best_pick`); kept 0 here so the
> module stays pure and unit-testable. `champ_top_full` on the test entries is a convenience
> the driver passes through; `compute` reads only `latest_champion`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_live_stats.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/live_stats.py tests/test_live_stats.py
git commit -m "Add live_stats aggregation + LaTeX macro rendering"
```

---

## Task 3: Interpretation draft (`draft_interpretation.py`)

**Files:**
- Create: `scripts/draft_interpretation.py`
- Test: `tests/test_draft_interpretation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_draft_interpretation.py
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import draft_interpretation as di

ENTRY = {"fixture": "Mexico v South Africa", "result": [2, 0],
         "pre": {"pick": [2, 1], "probs_HDA": [0.6718, 0.2087, 0.1193]},
         "post": {"points": 1, "brier": 0.1655, "p_outcome": 0.6718, "info_bits": 0.0011}}

def test_templated_is_deterministic_and_mentions_key_facts():
    a = di.templated(ENTRY)
    b = di.templated(ENTRY)
    assert a == b                       # deterministic
    assert "1 of 3" in a or "1/3" in a  # the points
    assert "0.001" in a                 # info_bits, low-movement story

def test_draft_falls_back_to_template_without_api():
    text, source = di.draft(ENTRY, corrections="", use_api=False)
    assert source == "template"
    assert text == di.templated(ENTRY)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_draft_interpretation.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/draft_interpretation.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_draft_interpretation.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/draft_interpretation.py tests/test_draft_interpretation.py
git commit -m "Add interpretation drafter: deterministic template + Claude-with-fallback"
```

---

## Task 4: Evolution renderer (`render_evolution.py`)

**Files:**
- Create: `scripts/render_evolution.py`
- Test: `tests/test_render_evolution.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render_evolution.py
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import render_evolution as re_

SAMPLE = ("FROZEN ABOVE\n"
          "% LIVE-EVOLUTION-TABLE:START\n"
          "old table\n"
          "% LIVE-EVOLUTION-TABLE:END\n"
          "FROZEN BELOW\n")

ENTRIES = [
    {"match": 1, "fixture": "Mexico v South Africa", "result": [2, 0],
     "failure_mode": None,
     "pre": {"pick": [2, 1]},
     "post": {"points": 1, "brier": 0.1655, "info_bits": 0.0011},
     "interpretation": "A likely home win arrived; the title race barely moved."},
]

def test_replace_markers_only_touches_the_block():
    out = re_.replace_markers(SAMPLE, "LIVE-EVOLUTION-TABLE", "NEW\nROWS")
    assert "FROZEN ABOVE" in out and "FROZEN BELOW" in out
    assert "old table" not in out
    assert "NEW\nROWS" in out

def test_missing_marker_raises():
    try:
        re_.replace_markers("no markers here", "LIVE-EVOLUTION-TABLE", "x")
        assert False, "expected ValueError"
    except ValueError:
        pass

def test_frozen_hash_ignores_marker_contents():
    h1 = re_.frozen_hash(SAMPLE)
    changed = re_.replace_markers(SAMPLE, "LIVE-EVOLUTION-TABLE", "totally different")
    assert re_.frozen_hash(changed) == h1     # frozen text unchanged

def test_ledger_table_has_one_row_per_entry():
    tex = re_.ledger_table(ENTRIES)
    assert "Mexico v South Africa" in tex
    assert "2--0" in tex          # result rendered with en-dash
    assert tex.count(r"\\") >= 1  # at least one table row
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_render_evolution.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/render_evolution.py
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
    pre = tex.split(start, 1)[0]
    post = tex.split(end, 1)[1]
    return f"{pre}{start}\n{content}\n{end}{post}"


def frozen_hash(tex):
    """Hash everything OUTSIDE every LIVE-EVOLUTION marker block."""
    stripped = _re.sub(r"% LIVE-EVOLUTION-[A-Z]+:START.*?% LIVE-EVOLUTION-[A-Z]+:END",
                       "", tex, flags=_re.DOTALL)
    return hashlib.sha256(stripped.encode()).hexdigest()


def _score(result):
    return f"{result[0]}--{result[1]}"


def ledger_table(entries):
    rows = []
    for e in entries:
        fm = e["failure_mode"] or "--"
        rows.append(
            f"{e['match']} & {e['fixture']} & {e['pre']['pick'][0]}--{e['pre']['pick'][1]} "
            f"& {_score(e['result'])} & {e['post']['points']} & {e['post']['brier']:.3f} "
            f"& {e['post']['info_bits']:.3f} & {fm} \\\\")
    return "\n".join(rows)


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_render_evolution.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/render_evolution.py tests/test_render_evolution.py
git commit -m "Add evolution renderer: guarded markers, frozen-hash, ledger + narrative"
```

---

## Task 5: Paper LaTeX scaffolding (markers + macros)

**Files:**
- Modify: `paper/Avraa_WC2026_paper.tex` (inside `sec:evolution` ~L263; preamble; abstract; conclusion)
- Create: `paper/live_stats.tex` (initial placeholder so the paper builds before the first run)

- [ ] **Step 1: Add the macro input and an initial `live_stats.tex`**

Create `paper/live_stats.tex`:
```latex
% GENERATED by scripts/live_stats.py — do not edit by hand.
\def\liveDocumented{0}
\def\liveCumPoints{0}
\def\liveMeanBrier{0.00}
\def\liveExactRate{0.00}
```

In `paper/Avraa_WC2026_paper.tex`, in the preamble (after the last `\usepackage`), add:
```latex
\input{live_stats}
```

- [ ] **Step 2: Insert the marker blocks into `sec:evolution`**

Find `\subsection{Forecast evolution: a pre-registered live study}\label{sec:evolution}` (~L263).
Immediately AFTER its existing frozen framing paragraph, insert:
```latex

% LIVE-EVOLUTION-TABLE:START
% LIVE-EVOLUTION-TABLE:END

\medskip
\noindent\textit{Match-by-match notes (informative results).}

% LIVE-EVOLUTION-NARRATIVE:START
% LIVE-EVOLUTION-NARRATIVE:END
```

- [ ] **Step 3: Add the two tagged-twin living numbers**

In the abstract (or conclusion running-performance sentence), append a live companion sentence
that uses the macros (frozen literals elsewhere stay unchanged):
```latex
As of the live scorecard, the entry has accrued \liveCumPoints{} pool points across
\liveDocumented{} graded matches at a mean Brier score of \liveMeanBrier{}.
```

- [ ] **Step 4: Verify the paper still builds**

Run: `cd paper && latexmk -pdf -interaction=nonstopmode Avraa_WC2026_paper.tex`
Expected: builds a PDF with no error; the live sentence reads "0 pool points across 0 graded matches at a mean Brier score of 0.00".

- [ ] **Step 5: Commit**

```bash
git add paper/Avraa_WC2026_paper.tex paper/live_stats.tex
git commit -m "Paper: add LIVE-EVOLUTION markers, live_stats macros, tagged-twin scorecard line"
```

---

## Task 6: The driver (`update_after_match.py`)

**Files:**
- Create: `scripts/update_after_match.py`
- Test: `tests/test_update_after_match.py`

This task wires the pure modules into a working command. The git/latexmk steps are isolated in
small functions so the core logic is testable without side effects.

- [ ] **Step 1: Write the failing test (core logic, no git/latex)**

```python
# tests/test_update_after_match.py
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import update_after_match as uam

TRAJ = [
    {"phase": "pre", "match": 1, "kickoff": "2026-06-11T19:00:00Z",
     "champion": {"Spain": 0.2711, "Argentina": 0.1768},
     "market_champion": {"Spain": 0.164}, "info_bits": 0.0,
     "result": None, "performance": None},
    {"phase": "post", "match": 1, "kickoff": "2026-06-11T19:00:00Z",
     "champion": {"Spain": 0.2711, "Argentina": 0.1815}, "info_bits": 0.0011,
     "result": [2, 0],
     "performance": {"points": 1, "ev_points": 0.855, "p_outcome": 0.6718, "brier": 0.1655}},
]
EXP = [{"match": 1, "group": "A", "home": "Mexico", "away": "South Africa",
        "pick": [2, 1], "probs_HDA": [0.6718, 0.2087, 0.1193], "lh": 1.9, "la": 0.65}]

def test_pending_matches_are_finalized_but_undocumented(tmp_path):
    idx = tmp_path / "index.json"
    pending = uam.pending_matches(TRAJ, idx)
    assert pending == [1]

def test_re_ev_delta_uses_ev_pick():
    # realistic pick 2-1 scored 1; EV pick 1-0 also scores 1 vs 2-0 -> delta 0
    d = uam.re_ev_delta_for(EXP[0], [2, 0], realistic_points=1)
    assert d == 0

def test_build_full_entry_attaches_interpretation_and_failure_tag(tmp_path):
    e = uam.build_full_entry(1, TRAJ, EXP, forecast_commit="abc1234",
                             documented_at="2026-06-11T21:10:58Z", use_api=False)
    assert e["interpretation"]                      # non-empty (templated)
    assert e["interpretation_source"] == "template"
    assert e["failure_mode"] in (None, *uam.mb.FAILURE_MODES)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_update_after_match.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# scripts/update_after_match.py
"""Driver: turn a finalized match into a paper revision. In CI it runs hands-off;
locally `--reopen M` lets the author replace an interpretation (the only human
step). Writes only the living layer; a frozen-hash check guards the rest."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import match_book as mb
import live_stats as ls
import render_evolution as rev
import draft_interpretation as di
from ev321 import best_pick
from realism_backtest import realistic, score_321

DATA = ROOT / "data"
PAPER = ROOT / "paper"
TRAJ_PATH = DATA / "trajectory_v2.json"
EXP_PATH = DATA / "match_expectations.json"
INDEX = PAPER / "match_book" / "index.json"
CORRECTIONS = PAPER / "match_book" / "corrections.md"
REVISIONS = PAPER / "REVISIONS.md"
PAPER_TEX = PAPER / "Avraa_WC2026_paper.tex"
LIVE_STATS_TEX = PAPER / "live_stats.tex"


def _load(p, default):
    return json.loads(Path(p).read_text()) if Path(p).exists() else default


def pending_matches(trajectory, index_path):
    posts = {r["match"] for r in trajectory if r["phase"] == "post"}
    done = set(mb.documented_matches(index_path))
    return sorted(posts - done)


def re_ev_delta_for(exp, result, realistic_points):
    """Running realistic-vs-EV pool-point delta for one match: realistic minus EV."""
    ev = best_pick(exp["lh"], exp["la"])
    ev_pts = score_321(list(ev), result[0], result[1])
    return realistic_points - ev_pts


def detect_failure_mode(entry, exp):
    """Coarse, documented first-pass; the human refines via --reopen.
    Flags systematic_rating_error when the model's modal outcome lost and it had
    assigned the realized outcome under 25%."""
    ph, pd, pa = entry["pre"]["probs_HDA"]
    modal = max(range(3), key=lambda i: (ph, pd, pa)[i])    # 0=H,1=D,2=A
    r = entry["result"]
    real = 0 if r[0] > r[1] else (1 if r[0] == r[1] else 2)
    if real != modal and (ph, pd, pa)[real] < 0.25:
        return "systematic_rating_error"
    return None


def build_full_entry(match, trajectory, expectations, forecast_commit,
                     documented_at, use_api):
    e = mb.build_entry(match, trajectory, expectations, forecast_commit, documented_at)
    exp = next(x for x in expectations if x["match"] == match)
    e["failure_mode"] = detect_failure_mode(e, exp)
    corrections = CORRECTIONS.read_text() if CORRECTIONS.exists() else ""
    text, source = di.draft(e, corrections, use_api)
    e["interpretation"], e["interpretation_source"] = text, source
    return e


def _entries_for_stats(index_path):
    """Load every documented entry back from disk for the aggregate pass."""
    out = []
    for m in mb.documented_matches(index_path):
        f = PAPER / "match_book" / f"M{m:03d}.md"
        out.append(mb.parse_markdown(f.read_text()))
    return out


def _git(*args):
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def _latexmk():
    subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode",
                    "Avraa_WC2026_paper.tex"], cwd=PAPER, check=True)


def revise(match, use_api=True, reopen_text=None):
    trajectory = _load(TRAJ_PATH, [])
    expectations = _load(EXP_PATH, [])
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entry_path = PAPER / "match_book" / f"M{match:03d}.md"
    if reopen_text is not None and entry_path.exists():
        e = mb.parse_markdown(entry_path.read_text())
        old = e["interpretation"]
        e["interpretation"], e["interpretation_source"] = reopen_text, "human"
        with CORRECTIONS.open("a") as fh:
            fh.write(f"\n## M{match} (reopened {now})\nDRAFT: {old}\nHUMAN: {reopen_text}\n")
    else:
        e = build_full_entry(match, trajectory, expectations, commit, now, use_api)
    entry_path.parent.mkdir(parents=True, exist_ok=True)
    entry_path.write_text(mb.to_markdown(e))
    mb.mark_documented(INDEX, match)

    # aggregate + render
    entries = _entries_for_stats(INDEX)
    latest_champ = next(r["champion"] for r in reversed(trajectory)
                        if r["phase"] == "post")
    stats = ls.compute(entries, latest_champ)
    stats["re_ev_delta"] = sum(
        re_ev_delta_for(next(x for x in expectations if x["match"] == en["match"]),
                        en["result"], en["post"]["points"]) for en in entries)
    LIVE_STATS_TEX.write_text(ls.render_macros(stats))

    tex = PAPER_TEX.read_text()
    before = rev.frozen_hash(tex)
    tex = rev.render_paper(tex, entries)
    after = rev.frozen_hash(tex)
    if before != after:
        raise SystemExit("ABORT: frozen region changed — refusing to write paper")
    PAPER_TEX.write_text(tex)

    with REVISIONS.open("a") as fh:
        fh.write(f"\n**Rev M{match:03d} ({e['fixture']} {e['result'][0]}-{e['result'][1]}).** "
                 f"Cumulative {stats['cum_points']} pts, mean Brier {stats['mean_brier']:.2f}; "
                 f"failure-mode {e['failure_mode'] or 'none'}. "
                 f"Updated evolution table + narrative; no frozen content changed.\n")
    print(f"Paper revised through Match {match} — {stats['documented']} documented · "
          f"{stats['cum_points']} pts · mean Brier {stats['mean_brier']:.3f} · "
          f"failure {e['failure_mode'] or 'none'}")
    return stats


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("match", type=int)
    ap.add_argument("--reopen", metavar="TEXT", default=None,
                    help="replace the interpretation with TEXT (human track)")
    ap.add_argument("--no-api", action="store_true", help="force templated draft")
    ap.add_argument("--build", action="store_true", help="run latexmk after writing")
    a = ap.parse_args(argv)
    revise(a.match, use_api=not a.no_api, reopen_text=a.reopen)
    if a.build:
        _latexmk()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_update_after_match.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/update_after_match.py tests/test_update_after_match.py
git commit -m "Add driver: pending detection, full entry, frozen-guarded render, REVISIONS"
```

---

## Task 7: End-to-end integration test on the real opener

**Files:**
- Test: `tests/test_paper_revision_integration.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/test_paper_revision_integration.py
"""Runs the real driver against the committed M1 records into a temp paper tree,
then asserts the living layer updated and the frozen layer did not."""
import json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import update_after_match as uam
import render_evolution as rev

def test_opener_revision_updates_living_not_frozen(tmp_path, monkeypatch):
    traj = json.loads((ROOT / "data" / "trajectory_v2.json").read_text())
    posts = [r for r in traj if r["phase"] == "post"]
    if not posts:
        import pytest; pytest.skip("no POST records yet")
    m = posts[0]["match"]

    # redirect the driver's paper paths into tmp
    paper = tmp_path / "paper"; (paper / "match_book").mkdir(parents=True)
    shutil.copy(ROOT / "paper" / "Avraa_WC2026_paper.tex", paper / "Avraa_WC2026_paper.tex")
    monkeypatch.setattr(uam, "PAPER", paper)
    monkeypatch.setattr(uam, "INDEX", paper / "match_book" / "index.json")
    monkeypatch.setattr(uam, "CORRECTIONS", paper / "match_book" / "corrections.md")
    monkeypatch.setattr(uam, "REVISIONS", paper / "REVISIONS.md")
    monkeypatch.setattr(uam, "PAPER_TEX", paper / "Avraa_WC2026_paper.tex")
    monkeypatch.setattr(uam, "LIVE_STATS_TEX", paper / "live_stats.tex")

    frozen_before = rev.frozen_hash((paper / "Avraa_WC2026_paper.tex").read_text())
    stats = uam.revise(m, use_api=False)
    tex_after = (paper / "Avraa_WC2026_paper.tex").read_text()

    assert stats["documented"] == 1
    assert (paper / "match_book" / f"M{m:03d}.md").exists()
    assert (paper / "live_stats.tex").exists()
    assert "LIVE-EVOLUTION-TABLE:START" in tex_after
    assert rev.frozen_hash(tex_after) == frozen_before     # frozen layer untouched
```

- [ ] **Step 2: Run it**

Run: `python3 -m pytest tests/test_paper_revision_integration.py -q`
Expected: PASS (1 passed) — requires Task 5's markers present in the paper.

- [ ] **Step 3: Commit**

```bash
git add tests/test_paper_revision_integration.py
git commit -m "Add end-to-end integration test: living updates, frozen invariant"
```

---

## Task 8: Isolated CI workflow (`paper-revision.yml`)

**Files:**
- Create: `.github/workflows/paper-revision.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: paper-revision
on:
  workflow_run:
    workflows: ["live-update-v2"]
    types: [completed]
  workflow_dispatch: {}
permissions:
  contents: write
concurrency:
  group: paper-revision
  cancel-in-progress: false
jobs:
  revise:
    if: ${{ github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install anthropic SDK
        run: pip install anthropic
      - name: Install TeX Live (latexmk)
        run: |
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended latexmk
      - name: Revise paper for each pending match
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python3 - <<'PY'
          import sys; sys.path.insert(0, "scripts")
          import json
          import update_after_match as uam
          traj = json.load(open("data/trajectory_v2.json"))
          for m in uam.pending_matches(traj, uam.INDEX):
              print("revising match", m)
              uam.revise(m, use_api=True)
              uam._latexmk()
              import shutil, os
              os.makedirs("paper/_snapshots", exist_ok=True)
              shutil.copy("paper/Avraa_WC2026_paper.pdf",
                          f"paper/_snapshots/Avraa_WC2026_paper_M{m:03d}.pdf")
          PY
      - name: Upload version snapshots (artifacts, not committed)
        uses: actions/upload-artifact@v4
        with:
          name: paper-versions
          path: paper/_snapshots/*.pdf
          retention-days: 90
      - name: Commit living layer only (allowlisted)
        run: |
          CHANGED=$(git status --porcelain \
            paper/Avraa_WC2026_paper.tex paper/live_stats.tex paper/REVISIONS.md paper/match_book)
          if [ -z "$CHANGED" ]; then echo "no changes."; exit 0; fi
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          for f in paper/Avraa_WC2026_paper.tex paper/live_stats.tex paper/REVISIONS.md; do
            [ -f "$f" ] && git add "$f"
          done
          git add paper/match_book
          for f in $(git diff --cached --name-only); do
            case "$f" in
              paper/Avraa_WC2026_paper.tex|paper/live_stats.tex|paper/REVISIONS.md|paper/match_book/*) ;;
              *) echo "REFUSING: non-allowlisted file staged: $f"; exit 1 ;;
            esac
          done
          git commit -m "paper: revise live study through pending matches"
          git pull --rebase origin "$GITHUB_REF_NAME" || true
          git push
```

- [ ] **Step 2: Add the snapshot dir to .gitignore**

Append to `.gitignore`:
```
paper/_snapshots/
paper/Avraa_WC2026_paper.pdf
```

- [ ] **Step 3: Validate the YAML locally**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/paper-revision.yml'))"`
Expected: no error (install pyyaml if needed: `pip install pyyaml`).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/paper-revision.yml .gitignore
git commit -m "Add isolated paper-revision CI: chains off v2, latexmk, artifact snapshots"
```

---

## Task 9: Manual run + full suite + docs

**Files:**
- Modify: `README` of the pipeline behavior is out of scope (frozen public README untouched).

- [ ] **Step 1: Run the whole suite**

Run: `python3 -m pytest tests/ -q`
Expected: all green, including the 5 new test files.

- [ ] **Step 2: Do one real local revision end-to-end (templated, no API, with build)**

Run:
```bash
python3 scripts/update_after_match.py 1 --no-api --build
```
Expected: prints "Paper revised through Match 1 …"; `paper/match_book/M001.md`,
`paper/live_stats.tex`, `paper/REVISIONS.md` exist; `paper/Avraa_WC2026_paper.pdf` built;
the live scorecard sentence now shows real numbers.

- [ ] **Step 3: Confirm idempotency**

Run: `python3 scripts/update_after_match.py 1 --no-api` then check `pending_matches`:
```bash
python3 -c "import sys; sys.path.insert(0,'scripts'); import json, update_after_match as u; print(u.pending_matches(json.load(open('data/trajectory_v2.json')), u.INDEX))"
```
Expected: `[]` for already-documented matches.

- [ ] **Step 4: Commit the first real revision artifacts**

```bash
git add paper/match_book paper/live_stats.tex paper/REVISIONS.md paper/Avraa_WC2026_paper.tex
git commit -m "First live-study revision (Match 1), generated locally"
```

> NOTE: keep these commits LOCAL until you decide to push (consistent with the held-local
> docs). The CI workflow + secret go live only when you push `paper-revision.yml` and add
> `ANTHROPIC_API_KEY` to repo secrets.

---

## Deferred from v1 (explicit scope cuts)

- **Champion-trajectory figure refresh** (spec §4 Component 4). v1 carries the full quantitative
  record in the ledger table + `live_stats` macros, which is sufficient for the living study. The
  figure is a presentation nice-to-have that can reuse the existing plotting (`scripts/plot_replay.py`,
  `data/trajectory_v2.json`) behind a third `% LIVE-EVOLUTION-FIGURE` marker in a follow-up. Cutting
  it keeps v1 free of a matplotlib build dependency in CI.
- **Secondary surfaces** (public markdown dossier diary, README block) — spec non-goals for v1.
- **Claude prompt tuning / few-shot growth** beyond the basic `corrections.md` read — the loop is
  wired (Tasks 3 + 6); refining the prompt is left to live calibration.

## Self-review notes (coverage check vs. spec)

- Spec §3 frozen/living split → Task 4 `frozen_hash` + Task 6 abort guard + Task 5 markers/macros.
- Spec §4 Components 1–10 → Task 6 driver (1,5,7,9), Task 1 (2), Task 3 (3,3b), Task 4 (4), Task 8 (8 versioning via artifacts, 10 CI), Task 6 REVISIONS (9), Task 4 markers (6 guard).
- Spec §9 decisions → latexmk (Tasks 5–8), Match-Book-only (Task 4 narrative highlights), tagged twins cum-points + mean-Brier (Task 5 Step 3), artifact snapshots (Task 8), Claude+fallback (Task 3).
- Self-learning loop (corrections.md) → written on `--reopen` (Task 6 `revise`), read by the drafter (Task 3 `_build_prompt`).
- Failure-mode tally → Task 2 `compute`; coarse detection Task 6 `detect_failure_mode` (human-refinable, documented).
