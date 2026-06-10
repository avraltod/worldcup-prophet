# Live Update Automation Implementation Plan (Project B — group stage)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A daily GitHub Actions cron that fetches finished group-stage scores from ESPN, re-conditions the frozen forecast, scores the day, and updates the README "Results tracking" block — committed and pushed automatically, or held with an alert if anything is uncertain.

**Architecture:** Two new pure-Python modules (`scripts/fetch_results.py` data+gate, `scripts/live_update.py` orchestrator) reuse the existing `record_update.py`/`score_day.py` via subprocess. A workflow (`.github/workflows/live-update.yml`) runs the orchestrator on cron, then commits an allowlisted file set as `github-actions[bot]`. Zero third-party deps (stdlib only); zero secrets (ESPN + Polymarket are public, push uses the built-in `GITHUB_TOKEN`).

**Tech Stack:** Python 3.12 stdlib (`urllib`, `json`, `datetime`, `subprocess`), pytest, GitHub Actions. Source spec: `archive/docs_superpowers/specs/2026-06-10-live-update-automation-design.md`.

**Scope:** GROUP STAGE only (match numbers 4–75, the `GROUP_FIXTURES` rows). Knockouts are a separate fast-follow. `score_day.py` already skips non-group pairings, and `map_to_fixture` only matches group fixtures, so KO events fetched from ESPN are ignored by construction.

**Key data shapes (verified against the live repo + ESPN, 2026-06-10):**
- ESPN endpoint: `GET https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=YYYYMMDD` → `{"events":[{ "date":"2026-06-11T19:00Z", "competitions":[{ "status":{"type":{"state","completed","detail"}}, "competitors":[{"homeAway":"home|away","team":{"displayName":...},"score":"2"}] }] }]}`. A finished group match reads `state="post", completed=true, detail="FT"`.
- `scripts/fixtures.py`: `GROUP_FIXTURES = [(row, group, home, away), ...]` (rows 4–75); `canon(name)` = `ALIASES.get(name.strip().lower(), name)`.
- `scripts/record_update.py '<{"group":{"4":[2,0]}}>' "<label>"` merges into `data/results_log.json`, re-conditions, **appends** a snapshot to `data/trajectory.json` with keys: `label, n_played, info_bits, champion {team:prob}, market_champion {team:prob}, top_movers [[team, pp], ...]`.
- `scripts/score_day.py '<[{"home","away","hg","ag"}, ...]>'` appends `experiment/ledger.csv` (group pairings only; ignores others).
- `data/results_log.json` shape: `{"group": {"<matchno>": [hg, ag]}, "ko": {...}}`; the group keys are **strings**.

**Allowlist (the only paths automation may write):** `data/results_log.json`, `data/trajectory.json`, `experiment/ledger.csv`, `README.md`.

---

### Task 1: ESPN parsing + fixture mapping (pure functions)

**Files:**
- Create: `scripts/fetch_results.py`
- Create: `tests/test_fetch_results.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fetch_results.py
import sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_results as fr

SAMPLE = {"events": [
    {"date": "2026-06-11T19:00Z", "competitions": [{
        "status": {"type": {"state": "post", "completed": True, "detail": "FT"}},
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "Mexico"}, "score": "2"},
            {"homeAway": "away", "team": {"displayName": "South Africa"}, "score": "1"}]}]},
    {"date": "2026-06-12T02:00Z", "competitions": [{
        "status": {"type": {"state": "in", "completed": False, "detail": "2nd Half"}},
        "competitors": [
            {"homeAway": "home", "team": {"displayName": "South Korea"}, "score": "0"},
            {"homeAway": "away", "team": {"displayName": "Czechia"}, "score": "0"}]}]},
]}

def test_parse_extracts_score_and_finality():
    rows = fr.parse_scoreboard(SAMPLE)
    assert len(rows) == 2
    m = rows[0]
    assert m["home"] == "Mexico" and m["away"] == "South Africa"
    assert m["hg"] == 2 and m["ag"] == 1
    assert m["final"] is True
    assert m["kickoff"] == dt.datetime(2026, 6, 11, 19, 0, tzinfo=dt.timezone.utc)
    assert rows[1]["final"] is False

def test_map_to_fixture_matches_and_orients():
    # exact orientation
    assert fr.map_to_fixture("Mexico", "South Africa")[0] == 4
    # reversed orientation flags reversed=True, keeps the canonical fixture row
    r, fh, fa, rev = fr.map_to_fixture("South Africa", "Mexico")
    assert r == 4 and fh == "Mexico" and fa == "South Africa" and rev is True
    # non-group / unknown pairing -> None
    assert fr.map_to_fixture("Mars", "Venus") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_fetch_results.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_results'`.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/fetch_results.py
"""ESPN scoreboard fetch + group-fixture mapping for the live update pipeline.
Pure parsing/mapping functions (no side effects) + a thin urllib fetch.
Group stage only: maps ESPN events to GROUP_FIXTURES rows 4-75."""
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import GROUP_FIXTURES, canon

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

# ESPN displayName (lowercased) -> our GROUP_FIXTURES name, for names that differ.
# Extended/verified by Task 2 against the live 2026 schedule.
ESPN_ALIASES = {
    "usa": "United States",
    "korea republic": "South Korea",
    "ir iran": "Iran",
    "türkiye": "Turkey",
    "turkiye": "Turkey",
    "côte d'ivoire": "Ivory Coast",
    "cote d'ivoire": "Ivory Coast",
    "cabo verde": "Cape Verde",
    "dr congo": "Congo DR",
    "czech republic": "Czechia",
}


def _espn_name(name):
    """Normalize an ESPN display name to our fixture vocabulary, then canon()."""
    return canon(ESPN_ALIASES.get(name.strip().lower(), name))


_FIX_ROW = {(_espn_name(h), _espn_name(a)): r for r, g, h, a in GROUP_FIXTURES}
_FIX_NAMES = {(_espn_name(h), _espn_name(a)): (h, a) for r, g, h, a in GROUP_FIXTURES}


def _score(competitor):
    try:
        return int(competitor.get("score"))
    except (TypeError, ValueError):
        return None


def parse_scoreboard(payload):
    """ESPN scoreboard JSON -> list of {home, away, hg, ag, kickoff(UTC aware), final}."""
    out = []
    for ev in payload.get("events", []):
        comp = ev["competitions"][0]
        st = comp["status"]["type"]
        final = (st.get("state") == "post" and st.get("completed") is True
                 and st.get("detail") == "FT")
        sides = {c["homeAway"]: c for c in comp["competitors"]}
        if "home" not in sides or "away" not in sides:
            continue
        out.append({
            "home": sides["home"]["team"]["displayName"],
            "away": sides["away"]["team"]["displayName"],
            "hg": _score(sides["home"]),
            "ag": _score(sides["away"]),
            "kickoff": dt.datetime.fromisoformat(ev["date"].replace("Z", "+00:00")),
            "final": final,
        })
    return out


def map_to_fixture(home, away):
    """Return (matchno, fixture_home, fixture_away, reversed) or None.
    `reversed` is True when ESPN's home is the fixture's away team."""
    ch, ca = _espn_name(home), _espn_name(away)
    if (ch, ca) in _FIX_ROW:
        return (_FIX_ROW[(ch, ca)], *_FIX_NAMES[(ch, ca)], False)
    if (ca, ch) in _FIX_ROW:
        return (_FIX_ROW[(ca, ch)], *_FIX_NAMES[(ca, ch)], True)
    return None


def fetch_dates(dates, opener=urllib.request.urlopen):
    """Fetch + parse ESPN scoreboard for each YYYYMMDD string. opener is injectable."""
    rows = []
    for d in dates:
        with opener(f"{ESPN_URL}?dates={d}", timeout=30) as resp:
            rows += parse_scoreboard(json.loads(resp.read().decode()))
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_fetch_results.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_results.py tests/test_fetch_results.py
git commit -m "Add ESPN scoreboard parser + group-fixture mapping"
```

---

### Task 2: Verify every 2026 group fixture maps (name-alias hardening)

**Files:**
- Create: `tests/test_name_mapping.py`
- Create: `data/espn_group_snapshot.json` (captured ESPN payloads, committed so the test runs offline/deterministically)
- Modify: `scripts/fetch_results.py` (extend `ESPN_ALIASES` until all 72 map)

- [ ] **Step 1: Capture the live ESPN group-stage payloads once**

Run (group stage is 2026-06-11 .. 2026-06-27):

```bash
python3 - <<'PY'
import json, urllib.request, datetime as dt
from pathlib import Path
url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
out = {}
d = dt.date(2026, 6, 11)
while d <= dt.date(2026, 6, 27):
    s = d.strftime("%Y%m%d")
    with urllib.request.urlopen(f"{url}?dates={s}", timeout=30) as r:
        out[s] = json.loads(r.read().decode())
    d += dt.timedelta(days=1)
Path("data/espn_group_snapshot.json").write_text(json.dumps(out))
print("captured", len(out), "dates")
PY
```
Expected: `captured 17 dates`.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_name_mapping.py
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_results as fr
from fixtures import GROUP_FIXTURES

SNAP = json.loads((Path(__file__).resolve().parent.parent
                   / "data" / "espn_group_snapshot.json").read_text())

def test_all_72_group_fixtures_resolvable_from_espn():
    seen = set()
    unmapped = []
    for payload in SNAP.values():
        for m in fr.parse_scoreboard(payload):
            fx = fr.map_to_fixture(m["home"], m["away"])
            if fx is None:
                # only flag pairings that ESPN labels as this competition's group games;
                # genuine non-group events (none expected in the group window) would show here
                unmapped.append((m["home"], m["away"]))
            else:
                seen.add(fx[0])
    assert not unmapped, f"ESPN names not mapping to a fixture: {sorted(set(unmapped))}"
    expected_rows = {r for r, g, h, a in GROUP_FIXTURES}
    assert seen == expected_rows, f"missing rows: {sorted(expected_rows - seen)}"
```

- [ ] **Step 3: Run test, read the failures, extend `ESPN_ALIASES`**

Run: `python3 -m pytest tests/test_name_mapping.py -q`
Expected initially: FAIL listing any ESPN names that don't map (e.g. `('Korea Republic', ...)`). For each, add a `"<espn lower>": "<fixture name>"` entry to `ESPN_ALIASES` in `scripts/fetch_results.py`. Re-run until both assertions pass.

NOTE: if ESPN has not yet published all 72 fixtures (some appear only after the draw bracket fills), the second assertion may list missing rows that aren't yet in ESPN. If so, change the second assertion to `assert seen, "no rows mapped"` and record in the commit message which rows ESPN had not yet listed, so Task 7's rehearsal re-checks closer to kickoff. Do NOT weaken the first assertion (unmapped names must always be zero).

- [ ] **Step 4: Confirm green**

Run: `python3 -m pytest tests/test_name_mapping.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_results.py data/espn_group_snapshot.json tests/test_name_mapping.py
git commit -m "Verify all 2026 group fixtures map from ESPN names; harden aliases"
```

---

### Task 3: Eligibility + confidence gate (pure function)

**Files:**
- Modify: `scripts/fetch_results.py` (add `eligible_targets`)
- Create: `tests/test_eligibility.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eligibility.py
import sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_results as fr

NOW = dt.datetime(2026, 6, 12, 13, 0, tzinfo=dt.timezone.utc)

def row(home, away, hg, ag, kickoff, final):
    return {"home": home, "away": away, "hg": hg, "ag": ag,
            "kickoff": kickoff, "final": final}

def t(h):  # helper: a kickoff h hours before NOW
    return NOW - dt.timedelta(hours=h)

def test_clean_matured_final_match_becomes_target():
    parsed = [row("Mexico", "South Africa", 2, 1, t(6), True)]
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {}, "ko": {}}, NOW)
    assert holds == []
    assert targets == {"4": [2, 1]}
    assert scored == [{"home": "Mexico", "away": "South Africa", "hg": 2, "ag": 1}]

def test_reversed_orientation_is_normalized_to_fixture():
    parsed = [row("South Africa", "Mexico", 1, 2, t(6), True)]  # ESPN home = fixture away
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {}, "ko": {}}, NOW)
    assert targets == {"4": [2, 1]} and holds == []  # oriented to Mexico(home) 2-1

def test_matured_but_not_final_holds_the_day():
    parsed = [row("Mexico", "South Africa", 1, 1, t(6), False)]
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {}, "ko": {}}, NOW)
    assert targets == {} and len(holds) == 1 and "not FT" in holds[0]

def test_unmatured_match_is_silently_excluded():
    parsed = [row("Mexico", "South Africa", 0, 0, t(1), False)]  # kicked off 1h ago
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {}, "ko": {}}, NOW)
    assert targets == {} and holds == []

def test_already_recorded_match_is_skipped():
    parsed = [row("Mexico", "South Africa", 2, 1, t(6), True)]
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {"4": [2, 1]}, "ko": {}}, NOW)
    assert targets == {} and holds == []

def test_score_out_of_bounds_holds():
    parsed = [row("Mexico", "South Africa", 99, 1, t(6), True)]
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {}, "ko": {}}, NOW)
    assert targets == {} and len(holds) == 1 and "out of bounds" in holds[0]

def test_non_group_event_ignored():
    parsed = [row("Mars", "Venus", 1, 0, t(6), True)]
    targets, holds, scored = fr.eligible_targets(parsed, {"group": {}, "ko": {}}, NOW)
    assert targets == {} and holds == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_eligibility.py -q`
Expected: FAIL — `AttributeError: module 'fetch_results' has no attribute 'eligible_targets'`.

- [ ] **Step 3: Implement `eligible_targets`**

Append to `scripts/fetch_results.py`:

```python
def eligible_targets(parsed, results_log, now_utc, maturity_hours=3):
    """Decide what to publish. Returns (targets, holds, scored).
      targets: {"<matchno>": [hg, ag]} oriented to the fixture, for record_update.py
      scored:  [{"home","away","hg","ag"}] oriented to the fixture, for score_day.py
      holds:   list of human-readable reasons; NON-EMPTY means hold everything.
    Rules: ignore non-group pairings; skip already-recorded; silently exclude
    matches not yet matured (kickoff within maturity_hours of now); for matured
    group matches, HOLD on not-final / missing / out-of-bounds score."""
    done = set(results_log.get("group", {}))
    cutoff = now_utc - dt.timedelta(hours=maturity_hours)
    targets, scored, holds = {}, [], []
    for m in parsed:
        fx = map_to_fixture(m["home"], m["away"])
        if fx is None:
            continue                      # not a group fixture -> not our concern
        rownum, fh, fa, rev = fx
        key = str(rownum)
        if key in done:
            continue                      # idempotent: already recorded
        if m["kickoff"] > cutoff:
            continue                      # not matured yet -> exclude silently
        if not m["final"]:
            holds.append(f"match {rownum} ({fh} v {fa}) matured but not FT")
            continue
        if m["hg"] is None or m["ag"] is None:
            holds.append(f"match {rownum} ({fh} v {fa}) FT but missing score")
            continue
        if not (0 <= m["hg"] <= 19 and 0 <= m["ag"] <= 19):
            holds.append(f"match {rownum} score out of bounds: {m['hg']}-{m['ag']}")
            continue
        hg, ag = (m["ag"], m["hg"]) if rev else (m["hg"], m["ag"])
        targets[key] = [hg, ag]
        scored.append({"home": fh, "away": fa, "hg": hg, "ag": ag})
    return targets, holds, scored
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_eligibility.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_results.py tests/test_eligibility.py
git commit -m "Add eligibility/confidence gate (strict finality, maturity, idempotency)"
```

---

### Task 4: README block rendering + marker replacement (pure functions) and README markers

**Files:**
- Create: `scripts/render_readme.py`
- Create: `tests/test_render_readme.py`
- Modify: `README.md` (convert the "Results tracking" placeholder to markers)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render_readme.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import render_readme as rr

TRAJ = [{
    "label": "2026-06-12", "n_played": 3, "info_bits": 0.0123,
    "champion": {"Spain": 0.262, "Argentina": 0.181, "France": 0.121},
    "market_champion": {"Spain": 0.155, "Argentina": 0.142, "France": 0.110},
    "top_movers": [["Mexico", 1.4], ["South Africa", -1.1]],
}]
LOG = {"group": {"4": [2, 1]}, "ko": {}}

def test_render_block_contains_key_facts():
    block = rr.render_results_block(TRAJ, LOG)
    assert "3/104" in block
    assert "0.012 bits" in block
    assert "Spain" in block and "26.2%" in block and "15.5%" in block
    assert "M4:" in block and "Mexico" in block and "2" in block

def test_replace_block_only_between_markers():
    text = ("intro\n<!-- LIVE-RESULTS:START -->\nOLD\n<!-- LIVE-RESULTS:END -->\noutro\n")
    out = rr.replace_readme_block(text, "NEW")
    assert "OLD" not in out and "NEW" in out
    assert out.startswith("intro\n") and out.rstrip().endswith("outro")

def test_replace_block_raises_if_markers_missing():
    import pytest
    with pytest.raises(ValueError):
        rr.replace_readme_block("no markers here", "NEW")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_render_readme.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'render_readme'`.

- [ ] **Step 3: Implement the renderer**

```python
# scripts/render_readme.py
"""Render the README 'Results tracking' block from the latest trajectory snapshot,
and replace only the text between the LIVE-RESULTS markers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import GROUP_FIXTURES

START = "<!-- LIVE-RESULTS:START -->"
END = "<!-- LIVE-RESULTS:END -->"
_NAMES = {r: (h, a) for r, g, h, a in GROUP_FIXTURES}


def render_results_block(trajectory, results_log):
    """Build the markdown block (string) from the last trajectory entry + the log."""
    snap = trajectory[-1]
    market = snap.get("market_champion") or {}
    lines = [
        f"_Last updated: {snap['label']} — {snap['n_played']}/104 matches played._",
        "",
        f"**Information gain in this update:** {snap['info_bits']:.3f} bits",
        "",
        "**Champion probability — model vs market (top 8):**",
        "",
        "| Team | Model | Market |",
        "|---|---|---|",
    ]
    for team, p in sorted(snap["champion"].items(), key=lambda x: -x[1])[:8]:
        mk = market.get(team)
        mk_s = f"{mk * 100:.1f}%" if mk is not None else "—"
        lines.append(f"| {team} | {p * 100:.1f}% | {mk_s} |")
    movers = snap.get("top_movers") or []
    if movers:
        lines += ["", "**Biggest moves:** " + ", ".join(
            f"{t} {'+' if d >= 0 else ''}{d}pp" for t, d in movers)]
    lines += ["", "**Recorded group results:**", ""]
    gl = results_log.get("group", {})
    for key in sorted(gl, key=lambda k: int(k)):
        h, a = _NAMES.get(int(key), ("?", "?"))
        hg, ag = gl[key]
        lines.append(f"- M{key}: {h} {hg}–{ag} {a}")
    return "\n".join(lines)


def replace_readme_block(text, block):
    """Replace text between the markers. Raises if markers are missing/duplicated."""
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("LIVE-RESULTS markers missing or duplicated")
    pre = text.split(START)[0]
    post = text.split(END, 1)[1]
    return f"{pre}{START}\n{block}\n{END}{post}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_render_readme.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Add the markers to README.md**

Replace the current "Results tracking" section (the italic placeholder) so it reads exactly:

```markdown
## Results tracking

<!-- LIVE-RESULTS:START -->
_Live results will appear here once the tournament begins (2026-06-11)._
<!-- LIVE-RESULTS:END -->
```

- [ ] **Step 6: Verify the markers parse**

Run:
```bash
python3 -c "import sys; sys.path.insert(0,'scripts'); import render_readme as rr; \
print(rr.replace_readme_block(open('README.md').read(), 'OK')[:0] or 'markers OK')"
```
Expected: `markers OK` (no exception → exactly one marker pair present).

- [ ] **Step 7: Commit**

```bash
git add scripts/render_readme.py tests/test_render_readme.py README.md
git commit -m "Add README results renderer + LIVE-RESULTS markers"
```

---

### Task 5: Orchestrator `live_update.py`

**Files:**
- Create: `scripts/live_update.py`
- Create: `tests/test_live_update.py`

- [ ] **Step 1: Write the failing test (gate behavior, no network, no subprocess)**

```python
# tests/test_live_update.py
import sys, json, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import live_update as lu

NOW = dt.datetime(2026, 6, 12, 13, 0, tzinfo=dt.timezone.utc)

def parsed_one(final=True, hours=6):
    return [{"home": "Mexico", "away": "South Africa", "hg": 2, "ag": 1,
             "kickoff": NOW - dt.timedelta(hours=hours), "final": final}]

def test_plan_holds_returns_exit_1(tmp_path):
    log = {"group": {}, "ko": {}}
    decision = lu.decide(parsed_one(final=False), log, NOW)
    assert decision.exit_code == 1 and decision.targets == {}
    assert any("not FT" in h for h in decision.holds)

def test_plan_noop_returns_exit_0(tmp_path):
    log = {"group": {"4": [2, 1]}, "ko": {}}        # already recorded
    decision = lu.decide(parsed_one(), log, NOW)
    assert decision.exit_code == 0 and decision.targets == {}

def test_plan_clean_returns_targets_exit_0():
    decision = lu.decide(parsed_one(), {"group": {}, "ko": {}}, NOW)
    assert decision.exit_code == 0 and decision.targets == {"4": [2, 1]}
    assert decision.scored[0]["home"] == "Mexico"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_live_update.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'live_update'`.

- [ ] **Step 3: Implement the orchestrator**

```python
# scripts/live_update.py
"""Daily live-update orchestrator (group stage).

Fetch ESPN scores -> gate -> (if clean & new) run record_update.py + score_day.py
-> re-render the README LIVE-RESULTS block. Writes ONLY the allowlisted files.
Exit codes: 0 = published or nothing-to-do; 1 = HOLD (alert). Use --dry-run to
print the decision without writing anything."""
import datetime as dt
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import fetch_results as fr
import render_readme as rr

RESULTS_LOG = ROOT / "data" / "results_log.json"
TRAJ = ROOT / "data" / "trajectory.json"
README = ROOT / "README.md"


@dataclass
class Decision:
    exit_code: int
    targets: dict = field(default_factory=dict)
    scored: list = field(default_factory=list)
    holds: list = field(default_factory=list)


def decide(parsed, results_log, now_utc):
    """Pure decision: parsed ESPN rows + current log -> Decision."""
    targets, holds, scored = fr.eligible_targets(parsed, results_log, now_utc)
    if holds:
        return Decision(exit_code=1, holds=holds)
    if not targets:
        return Decision(exit_code=0)
    return Decision(exit_code=0, targets=targets, scored=scored)


def _date_window(now_utc, back_days=3):
    """YYYYMMDD strings to query: covers UTC-boundary + a few missed runs."""
    return [(now_utc.date() - dt.timedelta(days=i)).strftime("%Y%m%d")
            for i in range(back_days + 1)]


def main(argv):
    dry = "--dry-run" in argv
    now = dt.datetime.now(dt.timezone.utc)
    parsed = fr.fetch_dates(_date_window(now))
    log = json.loads(RESULTS_LOG.read_text())
    decision = decide(parsed, log, now)

    if decision.holds:
        for h in decision.holds:
            print(f"HOLD: {h}", file=sys.stderr)
        return 1
    if not decision.targets:
        print("No new matured group matches; nothing to publish.")
        return 0

    print(f"Publishing {len(decision.targets)} match(es): {sorted(decision.targets)}")
    if dry:
        print("--dry-run: no files written.")
        return 0

    label = now.date().isoformat()
    subprocess.run([sys.executable, str(HERE / "record_update.py"),
                    json.dumps({"group": decision.targets}), label],
                   check=True, cwd=ROOT)
    subprocess.run([sys.executable, str(HERE / "score_day.py"),
                    json.dumps(decision.scored)], check=True, cwd=ROOT)

    trajectory = json.loads(TRAJ.read_text())
    log_after = json.loads(RESULTS_LOG.read_text())
    block = rr.render_results_block(trajectory, log_after)
    README.write_text(rr.replace_readme_block(README.read_text(), block))
    print("README results block updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_live_update.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Full suite + a real dry-run against live ESPN**

Run: `python3 -m pytest -q`
Expected: all tests pass.

Run: `python3 scripts/live_update.py --dry-run`
Expected (pre-kickoff, 2026-06-10): `No new matured group matches; nothing to publish.` and exit 0. (No files modified — confirm with `git status --porcelain`.)

- [ ] **Step 6: Commit**

```bash
git add scripts/live_update.py tests/test_live_update.py
git commit -m "Add live_update orchestrator (gate -> record_update/score_day -> README)"
```

---

### Task 6: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/live-update.yml`

- [ ] **Step 1: Write the workflow**

```yaml
# .github/workflows/live-update.yml
name: live-update
on:
  schedule:
    - cron: "0 13 * * *"      # daily 13:00 UTC; maturity gate makes exact time non-critical
  workflow_dispatch: {}        # allow manual runs for rehearsal
permissions:
  contents: write
concurrency:
  group: live-update
  cancel-in-progress: false
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Run live update (exit 1 => HOLD => this step fails => email)
        run: python3 scripts/live_update.py
      - name: Commit and push allowlisted changes
        run: |
          CHANGED=$(git status --porcelain \
            data/results_log.json data/trajectory.json experiment/ledger.csv README.md)
          if [ -z "$CHANGED" ]; then
            echo "No changes to publish."
            exit 0
          fi
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data/results_log.json data/trajectory.json experiment/ledger.csv README.md
          # belt-and-suspenders: refuse if anything outside the allowlist got staged
          for f in $(git diff --cached --name-only); do
            case "$f" in
              data/results_log.json|data/trajectory.json|experiment/ledger.csv|README.md) ;;
              *) echo "REFUSING: non-allowlisted file staged: $f"; exit 1 ;;
            esac
          done
          git commit -m "Live update: $(date -u +%Y-%m-%d)"
          git push
```

- [ ] **Step 2: Validate the YAML locally**

Run:
```bash
python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/live-update.yml')); print('yaml OK')" \
  2>/dev/null || python3 -c "import json; print('yaml lib absent — skip (Actions will validate)')"
```
Expected: `yaml OK` (or the skip message if PyYAML isn't installed locally — the workflow is plain and will validate on GitHub).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/live-update.yml
git commit -m "Add daily live-update GitHub Actions workflow"
```

---

### Task 7: Pre-kickoff rehearsal + push

**Files:** none (verification + integration)

- [ ] **Step 1: Push the branch so Actions can see the workflow**

```bash
git push origin main
```
Expected: push succeeds; the workflow file is now on the default branch.

- [ ] **Step 2: Manually trigger the workflow (rehearsal, pre-kickoff)**

Run:
```bash
gh workflow run live-update.yml
sleep 20
gh run list --workflow=live-update.yml --limit 1
```
Expected: a run appears. Pre-kickoff it should **succeed** with "No new matured group matches; nothing to publish." and produce **no commit** (verify `git fetch && git log --oneline -1 origin/main` is unchanged).

- [ ] **Step 3: Verify the hold path fails loudly (forced dry test)**

Temporarily confirm the gate's alerting by running the orchestrator against a synthetic not-final matured match locally (no writes, asserts exit 1):
```bash
python3 - <<'PY'
import sys, datetime as dt
sys.path.insert(0, "scripts")
import live_update as lu
now = dt.datetime(2026, 6, 12, 13, 0, tzinfo=dt.timezone.utc)
parsed = [{"home":"Mexico","away":"South Africa","hg":1,"ag":1,
           "kickoff": now - dt.timedelta(hours=6), "final": False}]
d = lu.decide(parsed, {"group":{}, "ko":{}}, now)
assert d.exit_code == 1 and d.holds, d
print("HOLD path OK:", d.holds[0])
PY
```
Expected: `HOLD path OK: match 4 (Mexico v South Africa) matured but not FT`.

- [ ] **Step 4: Confirm guards — locked files are untouchable**

Run:
```bash
grep -n "Avraa_Prediction_WC2026\|group_predictions" .github/workflows/live-update.yml || echo "locked files never referenced by workflow (good)"
```
Expected: the "good" message (the workflow only ever adds the 4 allowlisted paths).

- [ ] **Step 5: Final commit (if Step 2/3 required any alias or fix)**

```bash
git add -A && git commit -m "Live-update rehearsal fixes" || echo "nothing to commit"
git push origin main
```

---

## Self-review (completed by plan author)

- **Spec coverage:** ESPN-only fetch + UTC kickoff (Task 1) ✓; strict-finality/maturity/sanity/idempotency gate (Task 3) ✓; completeness = hold-the-day on a matured-not-final sibling (Task 3, `not m["final"]` → holds) ✓; README markers + render (Task 4) ✓; orchestrator calling reused scripts (Task 5) ✓; GitHub Actions cron 13:00 UTC + workflow_dispatch + `contents: write` + concurrency + `github-actions[bot]` (Task 6) ✓; allowlist enforced in workflow (Task 6) ✓; hard guard / locked files never written (Tasks 5–6: only 4 paths ever added) ✓; zero secrets, zero third-party deps (no requirements file; stdlib `urllib`) ✓; `--dry-run` rehearsal (Tasks 5, 7) ✓; name-mapping hardening for all 72 fixtures (Task 2) ✓; KO out of scope (map only matches group fixtures; `score_day` skips non-group) ✓.
- **Placeholder scan:** no TBD/TODO; every code step shows complete code; every command has an expected result. Task 2 Step 3 gives an explicit fallback rule (not a vague "handle it").
- **Name/signature consistency:** `parse_scoreboard`, `map_to_fixture` (returns `(matchno, home, away, reversed)`), `fetch_dates`, `eligible_targets(parsed, results_log, now_utc, maturity_hours=3)` → `(targets, holds, scored)`, `render_results_block(trajectory, results_log)`, `replace_readme_block(text, block)`, `decide(parsed, results_log, now_utc)` → `Decision(exit_code, targets, scored, holds)`. Used identically across Tasks 1, 3, 4, 5. `targets` keys are strings throughout (matches `results_log` group-key type). README markers `<!-- LIVE-RESULTS:START/END -->` identical in spec, Task 4, and Task 5 via `render_readme`.
- **One risk flagged for execution:** Task 2 may reveal ESPN hasn't published all 72 fixtures yet this far out; the fallback keeps the unmapped-names assertion strict while relaxing the row-completeness assertion, and Task 7 re-checks near kickoff.
