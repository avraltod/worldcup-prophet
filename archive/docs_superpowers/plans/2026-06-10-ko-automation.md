# Knockout-Stage Automation Implementation Plan (Project B fast-follow)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the live-update pipeline to publish knockout results — map each finished KO match to its FIFA match number (73–104), record the advancing team, re-condition the forecast, and update the README — auto-committed, or held with an alert on any uncertainty.

**Architecture:** A new pure resolver `scripts/ko_bracket.py` reconstructs the bracket deterministically by **importing** `condition.py`'s tables (no engine edits). `fetch_results.py` gains a `winner`-flag field, `map_ko_event`, and `eligible_ko_targets`; `live_update.py` merges group + KO targets into the one `record_update.py` call (which already consumes `{"group":…, "ko":…}`). Group-stage gate, allowlist, idempotency, and hold-on-doubt all carry over.

**Tech Stack:** Python 3.12 stdlib, pytest, the existing pipeline. Source spec: `archive/docs_superpowers/specs/2026-06-10-ko-automation-design.md`.

**Verified internals (condition.py, 2026-06-10):**
- `results_log["ko"]` = `{"<match_no>": "<winning team>"}` for 73–104; `condition.conditional_probs` uses `W[m] = ko_obs[m] if ko_obs[m] in (a,b) else simulate` (self-validates the winner against the slot).
- Importable module-level names in `condition.py`: `GROUPS` (grp→list of sheet rows), `ROW_MATCH` (row→official match#), `RATES` (row→`(lh, la, home, away)`), `R32` (`{m:(slot1,slot2)}`, slots like `"E1"`,`"A2"`,`"T74"`), `R16`/`QF`/`SF` (`{m:(feeder_m1, feeder_m2)}`), `TS` (third-place slot eligibility), `assign(groups)` → `{T_slot_match#: group}`.
- ESPN competitor carries `winner: true` on the advancer (incl. shootouts); `event.date` is UTC.

**Allowlist (unchanged):** `data/results_log.json`, `data/trajectory.json`, `experiment/ledger.csv`, `README.md`.

---

### Task 1: Deterministic bracket resolver `ko_bracket.py`

**Files:**
- Create: `scripts/ko_bracket.py`
- Create: `tests/test_ko_bracket.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ko_bracket.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ko_bracket as kb
from fixtures import GROUP_FIXTURES, ROW_MATCH


def _complete_group_results():
    """A deterministic, boundary-tie-free set of all 72 group results.
    Each team gets a unique strength; the stronger team wins by a margin that
    varies with the strength pair, so points AND goal-diff/goals-for are distinct
    within groups and across third-placed teams. If a boundary tie ever appears
    (resolver returns < 16 R32 pairings), perturb the margin formula below."""
    teams = []
    for r, g, h, a in GROUP_FIXTURES:
        for t in (h, a):
            if t not in teams:
                teams.append(t)
    strength = {t: i for i, t in enumerate(teams)}
    g_obs = {}
    for r, g, h, a in GROUP_FIXTURES:
        m = ROW_MATCH[r]
        sh, sa = strength[h], strength[a]
        margin = 1 + ((sh * sa) % 5)        # 1..5, varies GD/GF
        g_obs[str(m)] = [margin, 0] if sh > sa else [0, margin]
    return g_obs


def test_resolver_yields_full_R32_with_32_distinct_teams():
    log = {"group": _complete_group_results(), "ko": {}}
    pairings = kb.resolve_ko_pairings(log)
    r32 = {m: p for m, p in pairings.items() if 73 <= m <= 88}
    assert len(r32) == 16, f"expected 16 R32 pairings, got {len(r32)}"
    teams = [t for p in r32.values() for t in p]
    assert len(teams) == 32 and len(set(teams)) == 32  # no team appears twice

def test_resolver_is_deterministic():
    log = {"group": _complete_group_results(), "ko": {}}
    assert kb.resolve_ko_pairings(log) == kb.resolve_ko_pairings(log)

def test_incomplete_group_stage_yields_no_R32():
    log = {"group": {"1": [2, 1]}, "ko": {}}   # only 1 of 72
    pairings = kb.resolve_ko_pairings(log)
    assert all(m > 88 for m in pairings)        # no R32 pairings

def test_recorded_ko_winners_propagate_to_next_round():
    log = {"group": _complete_group_results(), "ko": {}}
    base = kb.resolve_ko_pairings(log)
    a74, a77 = sorted(base[74]), sorted(base[77])
    # record R32 winners feeding R16 match 89 = (74, 77)
    log["ko"] = {"74": a74[0], "77": a77[0]}
    p = kb.resolve_ko_pairings(log)
    assert p[89] == frozenset({a74[0], a77[0]})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_ko_bracket.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'ko_bracket'`.

- [ ] **Step 3: Implement `scripts/ko_bracket.py`**

```python
"""Deterministic knockout bracket resolver. Reconstructs which two teams meet in
each KO match (73-104) from the recorded results, reusing condition.py's bracket
tables. Pure: no side effects, no network. Imports condition.py but never edits it."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from condition import GROUPS, ROW_MATCH, RATES, R32, R16, QF, SF, assign

GROUP_LETTERS = "ABCDEFGHIJKL"


def _standings(g_obs):
    """Return (pos, thirds) or (None, None).
    pos: {"<grp>1": team, "<grp>2": team}; thirds: {grp: (third_team, key_tuple)}.
    None if the group stage is incomplete or a 1st/2nd/3rd boundary tie is ambiguous."""
    pos, thirds = {}, {}
    for grp in GROUP_LETTERS:
        st = {}
        for row in GROUPS[grp]:
            m = ROW_MATCH[row]
            if m not in g_obs:
                return None, None                      # group stage incomplete
            _lh, _la, home, away = RATES[row]
            hg, ag = g_obs[m]
            for t, f, ag_ in ((home, hg, ag), (away, ag, hg)):
                s = st.setdefault(t, [0, 0, 0])
                s[0] += 3 if f > ag_ else (1 if f == ag_ else 0)
                s[1] += f - ag_
                s[2] += f
        order = sorted(st, key=lambda t: tuple(st[t]), reverse=True)
        keys = [tuple(st[t]) for t in order]
        if keys[0] == keys[1] or keys[1] == keys[2]:    # boundary tie -> ambiguous
            return None, None
        pos[f"{grp}1"], pos[f"{grp}2"] = order[0], order[1]
        thirds[grp] = (order[2], tuple(st[order[2]]))
    return pos, thirds


def _r32_slots(g_obs):
    """Return {slot_name: team} for all R32 slots, or None if unresolved."""
    pos, thirds = _standings(g_obs)
    if pos is None:
        return None
    rk = sorted(thirds, key=lambda g: thirds[g][1], reverse=True)
    keys = [thirds[g][1] for g in rk]
    if len(keys) >= 9 and keys[7] == keys[8]:           # 8th/9th third tie -> ambiguous
        return None
    random.seed(2026)
    am = assign(rk[:8]) or assign(rk[:7] + [rk[8]])
    if am is None:
        return None
    slots = dict(pos)
    for t_match, grp in am.items():
        slots[f"T{t_match}"] = thirds[grp][0]
    return slots


def resolve_ko_pairings(results_log):
    """Return {match#: frozenset({teamA, teamB})} for KO matches whose both teams
    are known. R32 needs complete group standings; later rounds need recorded winners."""
    g_obs = {int(k): v for k, v in results_log.get("group", {}).items()}
    W = {int(k): v for k, v in results_log.get("ko", {}).items()}
    pairings = {}

    slots = _r32_slots(g_obs) if len(g_obs) >= 72 else None
    if slots is not None:
        for m, (s1, s2) in R32.items():
            if s1 in slots and s2 in slots:
                pairings[m] = frozenset({slots[s1], slots[s2]})

    for tab in (R16, QF, SF):
        for m, (m1, m2) in tab.items():
            if m1 in W and m2 in W:
                pairings[m] = frozenset({W[m1], W[m2]})
    if 101 in W and 102 in W:
        pairings[104] = frozenset({W[101], W[102]})       # final (champion match)
    if 101 in pairings and 102 in pairings and 101 in W and 102 in W:
        l1, l2 = pairings[101] - {W[101]}, pairings[102] - {W[102]}
        if len(l1) == 1 and len(l2) == 1:
            pairings[103] = frozenset(l1 | l2)            # bronze final (not conditioned)
    return pairings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_ko_bracket.py -q`
Expected: PASS (4 passed). If `test_resolver_yields_full_R32_with_32_distinct_teams` fails with fewer than 16 pairings, the synthetic fixture hit a boundary tie — change `margin = 1 + ((sh * sa) % 5)` to `1 + ((sh * sa + sh) % 7)` and re-run.

- [ ] **Step 5: Commit**

```bash
git add scripts/ko_bracket.py tests/test_ko_bracket.py
git commit -m "Add deterministic KO bracket resolver (reuses condition.py tables)"
```

---

### Task 2: ESPN `winner` field + `map_ko_event`

**Files:**
- Modify: `scripts/fetch_results.py` (extend `parse_scoreboard`; add `map_ko_event`)
- Create: `tests/test_map_ko_event.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_map_ko_event.py
import sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_results as fr
import ko_bracket as kb
from fixtures import GROUP_FIXTURES, ROW_MATCH


def _complete_group_results():
    teams = []
    for r, g, h, a in GROUP_FIXTURES:
        for t in (h, a):
            if t not in teams:
                teams.append(t)
    strength = {t: i for i, t in enumerate(teams)}
    out = {}
    for r, g, h, a in GROUP_FIXTURES:
        m = ROW_MATCH[r]
        sh, sa = strength[h], strength[a]
        margin = 1 + ((sh * sa) % 5)
        out[str(m)] = [margin, 0] if sh > sa else [0, margin]
    return out


def _ko_event(home, away, winner_name):
    return {"events": [{"date": "2026-06-29T19:00Z", "competitions": [{
        "status": {"type": {"state": "post", "completed": True, "detail": "FT-Pens"}},
        "competitors": [
            {"homeAway": "home", "team": {"displayName": home}, "score": "1",
             "winner": home == winner_name},
            {"homeAway": "away", "team": {"displayName": away}, "score": "1",
             "winner": away == winner_name}]}]}]}


def test_parse_extracts_winner_flag():
    rows = fr.parse_scoreboard(_ko_event("Argentina", "Croatia", "Argentina"))
    assert rows[0]["winner"] == "Argentina"

def test_map_ko_event_returns_matchno_and_winner():
    log = {"group": _complete_group_results(), "ko": {}}
    pairings = kb.resolve_ko_pairings(log)
    m74 = sorted(pairings[74])               # the two teams in KO match 74
    payload = _ko_event(m74[0], m74[1], m74[0])
    parsed = fr.parse_scoreboard(payload)[0]
    assert fr.map_ko_event(parsed, log) == (74, m74[0])

def test_map_ko_event_none_without_winner():
    log = {"group": _complete_group_results(), "ko": {}}
    pairings = kb.resolve_ko_pairings(log)
    m74 = sorted(pairings[74])
    payload = _ko_event(m74[0], m74[1], m74[0])
    parsed = fr.parse_scoreboard(payload)[0]
    parsed["winner"] = None
    assert fr.map_ko_event(parsed, log) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_map_ko_event.py -q`
Expected: FAIL — `KeyError: 'winner'` (parse_scoreboard has no winner field) / `AttributeError` (no `map_ko_event`).

- [ ] **Step 3: Implement**

In `scripts/fetch_results.py`, add `import ko_bracket` near the other imports (after the `from fixtures import …` line):

```python
import ko_bracket
```

In `parse_scoreboard`, add a `winner` key to the appended dict (compute it from the `winner: true` flag). Change the `out.append({...})` block to:

```python
        out.append({
            "home": sides["home"]["team"]["displayName"],
            "away": sides["away"]["team"]["displayName"],
            "hg": _score(sides["home"]),
            "ag": _score(sides["away"]),
            "kickoff": dt.datetime.fromisoformat(ev["date"].replace("Z", "+00:00")),
            "final": final,
            "winner": next((s["team"]["displayName"]
                            for s in (sides["home"], sides["away"])
                            if s.get("winner") is True), None),
        })
```

Add `map_ko_event` at the end of the file:

```python
def map_ko_event(parsed_match, results_log):
    """Map a parsed KO event to (match#, winner) using the ESPN winner flag and the
    bracket resolver. Returns None if no winner flag or no unique bracket slot."""
    w = parsed_match.get("winner")
    if not w:
        return None
    pair = frozenset({_espn_name(parsed_match["home"]), _espn_name(parsed_match["away"])})
    pairings = ko_bracket.resolve_ko_pairings(results_log)
    hits = [m for m, p in pairings.items() if p == pair]
    if len(hits) != 1:
        return None
    return hits[0], _espn_name(w)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_map_ko_event.py tests/test_fetch_results.py -q`
Expected: PASS (the new tests, and the existing fetch tests still green — `winner` is an added field).

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_results.py tests/test_map_ko_event.py
git commit -m "Add winner-flag parsing + map_ko_event"
```

---

### Task 3: KO eligibility gate `eligible_ko_targets`

**Files:**
- Modify: `scripts/fetch_results.py` (add `eligible_ko_targets`)
- Create: `tests/test_ko_eligibility.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ko_eligibility.py
import sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_results as fr
import ko_bracket as kb
from fixtures import GROUP_FIXTURES, ROW_MATCH

NOW = dt.datetime(2026, 6, 30, 13, 0, tzinfo=dt.timezone.utc)


def _complete_group_results():
    teams = []
    for r, g, h, a in GROUP_FIXTURES:
        for t in (h, a):
            if t not in teams:
                teams.append(t)
    strength = {t: i for i, t in enumerate(teams)}
    out = {}
    for r, g, h, a in GROUP_FIXTURES:
        m = ROW_MATCH[r]
        sh, sa = strength[h], strength[a]
        margin = 1 + ((sh * sa) % 5)
        out[str(m)] = [margin, 0] if sh > sa else [0, margin]
    return out


def _evt(home, away, winner, hours=6):
    return {"home": home, "away": away, "hg": 1, "ag": 1,
            "kickoff": NOW - dt.timedelta(hours=hours),
            "final": False, "winner": winner}

LOG = {"group": _complete_group_results(), "ko": {}}
PAIR74 = sorted(kb.resolve_ko_pairings(LOG)[74])

def test_clean_ko_match_becomes_target():
    parsed = [_evt(PAIR74[0], PAIR74[1], PAIR74[0])]
    ko_targets, holds = fr.eligible_ko_targets(parsed, LOG, NOW)
    assert ko_targets == {"74": PAIR74[0]} and holds == []

def test_matured_ko_without_winner_holds():
    parsed = [_evt(PAIR74[0], PAIR74[1], None)]
    ko_targets, holds = fr.eligible_ko_targets(parsed, LOG, NOW)
    assert ko_targets == {} and len(holds) == 1 and "no winner" in holds[0]

def test_unmatured_ko_excluded_silently():
    parsed = [_evt(PAIR74[0], PAIR74[1], PAIR74[0], hours=1)]
    ko_targets, holds = fr.eligible_ko_targets(parsed, LOG, NOW)
    assert ko_targets == {} and holds == []

def test_already_recorded_ko_skipped():
    log = {"group": LOG["group"], "ko": {"74": PAIR74[0]}}
    parsed = [_evt(PAIR74[0], PAIR74[1], PAIR74[0])]
    ko_targets, holds = fr.eligible_ko_targets(parsed, log, NOW)
    assert ko_targets == {} and holds == []

def test_group_fixture_is_not_a_ko_candidate():
    parsed = [_evt("Mexico", "South Africa", "Mexico")]
    ko_targets, holds = fr.eligible_ko_targets(parsed, LOG, NOW)
    assert ko_targets == {} and holds == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_ko_eligibility.py -q`
Expected: FAIL — `AttributeError: module 'fetch_results' has no attribute 'eligible_ko_targets'`.

- [ ] **Step 3: Implement** — append to `scripts/fetch_results.py`:

```python
def eligible_ko_targets(parsed, results_log, now_utc, maturity_hours=3):
    """Decide which KO matches to publish. Returns (ko_targets, holds).
      ko_targets: {"<match#>": winner}; holds: non-empty means hold everything.
    Group fixtures and not-yet-matured matches are excluded; matured KO matches are
    resolved iteratively to a fixpoint (a recorded R32 winner unlocks its R16 child).
    A matured KO match with no winner, or that maps to no unique bracket slot, holds."""
    cutoff = now_utc - dt.timedelta(hours=maturity_hours)
    candidates = []
    for m in parsed:
        if map_to_fixture(m["home"], m["away"]) is not None:
            continue                                     # group fixture, not KO
        if m["kickoff"] > cutoff:
            continue                                     # not matured yet
        candidates.append(m)
    if not candidates:
        return {}, []

    work = {"group": dict(results_log.get("group", {})),
            "ko": dict(results_log.get("ko", {}))}
    ko_targets, pending, progress = {}, list(candidates), True
    while progress and pending:
        progress, still = False, []
        for m in pending:
            res = map_ko_event(m, work)
            if res is None:
                still.append(m)
                continue
            matchno, winner = res
            key = str(matchno)
            if key not in work["ko"]:
                work["ko"][key] = winner
                ko_targets[key] = winner
            progress = True                              # mapped (new or already-recorded)
        pending = still

    holds = []
    for m in pending:
        if not m.get("winner"):
            holds.append(f"KO match ({m['home']} v {m['away']}) matured but no winner reported")
        else:
            holds.append(f"KO match ({m['home']} v {m['away']}) maps to no unique bracket slot "
                         f"(ambiguous standings or missing prior result)")
    return ko_targets, holds
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_ko_eligibility.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_results.py tests/test_ko_eligibility.py
git commit -m "Add KO eligibility gate with iterative fixpoint resolution"
```

---

### Task 4: Wire KO into the orchestrator

**Files:**
- Modify: `scripts/live_update.py` (`Decision.ko_targets`; `decide`; `main`)
- Modify: `tests/test_live_update.py` (add KO decide test)

- [ ] **Step 1: Write the failing test** — append to `tests/test_live_update.py`:

```python
def test_decide_includes_ko_targets(monkeypatch):
    import fetch_results as fr
    monkeypatch.setattr(fr, "eligible_targets", lambda *a, **k: ({}, [], []))
    monkeypatch.setattr(fr, "eligible_ko_targets", lambda *a, **k: ({"74": "Spain"}, []))
    d = lu.decide([], {"group": {}, "ko": {}}, NOW)
    assert d.exit_code == 0 and d.ko_targets == {"74": "Spain"} and d.targets == {}

def test_decide_holds_on_ko_hold(monkeypatch):
    import fetch_results as fr
    monkeypatch.setattr(fr, "eligible_targets", lambda *a, **k: ({}, [], []))
    monkeypatch.setattr(fr, "eligible_ko_targets", lambda *a, **k: ({}, ["KO match X holds"]))
    d = lu.decide([], {"group": {}, "ko": {}}, NOW)
    assert d.exit_code == 1 and "KO match X holds" in d.holds
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_live_update.py -q`
Expected: FAIL — `AttributeError: 'Decision' object has no attribute 'ko_targets'`.

- [ ] **Step 3: Implement** — in `scripts/live_update.py`:

Add `ko_targets` to the dataclass:
```python
@dataclass
class Decision:
    exit_code: int
    targets: dict = field(default_factory=dict)
    ko_targets: dict = field(default_factory=dict)
    scored: list = field(default_factory=list)
    holds: list = field(default_factory=list)
```

Replace `decide` with:
```python
def decide(parsed, results_log, now_utc):
    """Pure decision: parsed ESPN rows + current log -> Decision (group + KO)."""
    g_targets, g_holds, scored = fr.eligible_targets(parsed, results_log, now_utc)
    ko_targets, ko_holds = fr.eligible_ko_targets(parsed, results_log, now_utc)
    holds = g_holds + ko_holds
    if holds:
        return Decision(exit_code=1, holds=holds)
    if not g_targets and not ko_targets:
        return Decision(exit_code=0)
    return Decision(exit_code=0, targets=g_targets, ko_targets=ko_targets, scored=scored)
```

In `main`, replace the publish block (the `if not decision.targets: … nothing to publish` check and the two subprocess calls) with:
```python
    if not decision.targets and not decision.ko_targets:
        print("No new matured matches; nothing to publish.")
        return 0

    n = len(decision.targets) + len(decision.ko_targets)
    print(f"Publishing {n} match(es): group={sorted(decision.targets)} ko={sorted(decision.ko_targets)}")
    if dry:
        print("--dry-run: no files written.")
        return 0

    label = now.date().isoformat()
    subprocess.run([sys.executable, str(HERE / "record_update.py"),
                    json.dumps({"group": decision.targets, "ko": decision.ko_targets}), label],
                   check=True, cwd=ROOT)
    if decision.scored:
        subprocess.run([sys.executable, str(HERE / "score_day.py"),
                        json.dumps(decision.scored)], check=True, cwd=ROOT)
```

(Leave the README-render block below unchanged.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_live_update.py -q`
Expected: PASS (existing 3 + 2 new = 5 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/live_update.py tests/test_live_update.py
git commit -m "Wire KO targets into decide/main (combined record_update call)"
```

---

### Task 5: README knockout subsection

**Files:**
- Modify: `scripts/render_readme.py`
- Modify: `tests/test_render_readme.py`

- [ ] **Step 1: Write the failing test** — append to `tests/test_render_readme.py`:

```python
def test_render_includes_ko_results():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import ko_bracket as kb
    from fixtures import GROUP_FIXTURES, ROW_MATCH
    teams = []
    for r, g, h, a in GROUP_FIXTURES:
        for t in (h, a):
            if t not in teams:
                teams.append(t)
    strength = {t: i for i, t in enumerate(teams)}
    g = {}
    for r, gg, h, a in GROUP_FIXTURES:
        m = ROW_MATCH[r]
        sh, sa = strength[h], strength[a]
        margin = 1 + ((sh * sa) % 5)
        g[str(m)] = [margin, 0] if sh > sa else [0, margin]
    pair74 = sorted(kb.resolve_ko_pairings({"group": g, "ko": {}})[74])
    log = {"group": g, "ko": {"74": pair74[0]}}
    traj = [{"label": "2026-06-29", "n_played": 73, "info_bits": 0.05,
             "champion": {"Spain": 0.3}, "market_champion": {}, "top_movers": []}]
    block = rr.render_results_block(traj, log)
    assert "Knockout results" in block
    assert f"M74: {pair74[0]} def. {pair74[1]}" in block
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_render_readme.py -q`
Expected: FAIL — the new test (no "Knockout results" section yet).

- [ ] **Step 3: Implement** — in `scripts/render_readme.py`:

Change the import line to also import the resolver:
```python
from fixtures import GROUP_FIXTURES, ROW_MATCH
from ko_bracket import resolve_ko_pairings
```

At the end of `render_results_block`, before `return "\n".join(lines)`, add the KO block:
```python
    kol = results_log.get("ko", {})
    if kol:
        pairings = resolve_ko_pairings(results_log)
        lines += ["", "**Knockout results:**", ""]
        for key in sorted(kol, key=lambda k: int(k)):
            winner = kol[key]
            pair = pairings.get(int(key))
            loser = next(iter(pair - {winner}), "?") if pair else "?"
            lines.append(f"- M{key}: {winner} def. {loser}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_render_readme.py -q`
Expected: PASS (existing render tests + the new KO test).

- [ ] **Step 5: Commit**

```bash
git add scripts/render_readme.py tests/test_render_readme.py
git commit -m "Render knockout results subsection in README block"
```

---

### Task 6: KO publish integration test + full-suite gate

**Files:**
- Create: `tests/test_ko_integration.py`

- [ ] **Step 1: Write the test** (real `record_update` path with a fake KO event; restores files in teardown)

```python
# tests/test_ko_integration.py
"""End-to-end KO publish: seeded results_log (72 group + needed prior winners) +
fake KO ESPN fetch -> real record_update -> README KO block. Restores files in teardown."""
import sys, json, datetime as dt, shutil
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import live_update as lu
import fetch_results as fr
import ko_bracket as kb
from fixtures import GROUP_FIXTURES, ROW_MATCH

RESULTS_LOG = ROOT / "data" / "results_log.json"
TRAJ = ROOT / "data" / "trajectory.json"
README = ROOT / "README.md"
EXPERIMENT = ROOT / "experiment"


def _complete_group_results():
    teams = []
    for r, g, h, a in GROUP_FIXTURES:
        for t in (h, a):
            if t not in teams:
                teams.append(t)
    strength = {t: i for i, t in enumerate(teams)}
    out = {}
    for r, g, h, a in GROUP_FIXTURES:
        m = ROW_MATCH[r]
        sh, sa = strength[h], strength[a]
        margin = 1 + ((sh * sa) % 5)
        out[str(m)] = [margin, 0] if sh > sa else [0, margin]
    return out


@pytest.fixture
def restore_repo():
    saved = {p: (p.read_text() if p.exists() else None) for p in (RESULTS_LOG, TRAJ, README)}
    experiment_existed = EXPERIMENT.exists()
    yield
    for p, text in saved.items():
        if text is None:
            p.exists() and p.unlink()
        else:
            p.write_text(text)
    if not experiment_existed and EXPERIMENT.exists():
        shutil.rmtree(EXPERIMENT)


def test_ko_publish_records_winner_and_updates_readme(restore_repo, monkeypatch):
    group = _complete_group_results()
    RESULTS_LOG.write_text(json.dumps({"group": group, "ko": {}}))
    pair74 = sorted(kb.resolve_ko_pairings({"group": group, "ko": {}})[74])

    long_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=6)
    fake = [{"home": pair74[0], "away": pair74[1], "hg": 1, "ag": 1,
             "kickoff": long_ago, "final": False, "winner": pair74[0]}]
    monkeypatch.setattr(fr, "fetch_dates", lambda dates: fake)

    assert lu.main([]) == 0
    log = json.loads(RESULTS_LOG.read_text())
    assert log["ko"].get("74") == pair74[0]
    assert "Knockout results" in README.read_text()
```

- [ ] **Step 2: Run it**

Run: `python3 -m pytest tests/test_ko_integration.py -q -s`
Expected: PASS (runs a real 50k-sim conditioning; ~10-30s).

- [ ] **Step 3: Confirm pristine restore**

Run: `git status --porcelain`
Expected: shows only the new test file `tests/test_ko_integration.py` — `data/results_log.json`, `data/trajectory.json`, `README.md`, `experiment/` all restored by teardown. If any data/README file shows modified, the teardown failed — STOP.

- [ ] **Step 4: Full suite**

Run: `python3 -m pytest -q`
Expected: all pass (~2 min).

- [ ] **Step 5: Commit**

```bash
git add tests/test_ko_integration.py
git commit -m "Add KO publish integration test"
```

---

### Task 7: Rehearsal once the bracket is real (~2026-06-28)

**Files:** none (verification; run when the round of 32 is set)

- [ ] **Step 1: Capture a real KO snapshot and confirm mappings**

Once the group stage is complete and ESPN shows R32 fixtures, run:
```bash
python3 - <<'PY'
import sys, datetime as dt, json
sys.path.insert(0, "scripts")
import fetch_results as fr, ko_bracket as kb
log = json.loads(open("data/results_log.json").read())
dates = [(dt.date(2026, 6, 28) + dt.timedelta(days=i)).strftime("%Y%m%d") for i in range(4)]
parsed = fr.fetch_dates(dates)
pairings = kb.resolve_ko_pairings(log)
for m in parsed:
    if fr.map_to_fixture(m["home"], m["away"]) is None:   # KO event
        hit = [k for k, p in pairings.items() if p == frozenset({fr._espn_name(m["home"]), fr._espn_name(m["away"])})]
        print(m["home"], "v", m["away"], "->", hit or "UNMAPPED")
PY
```
Expected: every R32 fixture ESPN lists maps to exactly one match number. Any `UNMAPPED` means a standings tie or an alias gap — investigate before relying on the automation.

- [ ] **Step 2: Dry-run the orchestrator**

Run: `python3 scripts/live_update.py --dry-run`
Expected: reports the KO matches it would publish (or "nothing" if none matured), writes nothing.

- [ ] **Step 3: Confirm the live workflow is unchanged**

The existing `.github/workflows/live-update.yml` already runs `live_update.py` daily and needs no edit — KO support is entirely inside the Python it calls. Verify with one manual run:
```bash
gh workflow run live-update.yml && sleep 25 && gh run list --workflow=live-update.yml --limit 1
```
Expected: success.

---

## Self-review (completed by plan author)

- **Spec coverage:** resolver reusing condition tables w/o edits (Task 1) ✓; ESPN winner flag + match# mapping (Task 2) ✓; KO finality (winner-flag) + iterative fixpoint + hold-on-unmapped/no-winner + idempotency (Task 3) ✓; record winners + trajectory via combined record_update, group-only to score_day (Task 4) ✓; README KO subsection winner-def-loser (Task 5) ✓; integration + ~06-28 rehearsal, no condition.py edits, no new secrets/deps (Tasks 6–7) ✓; bronze 103 recorded not conditioned / final 104 (Task 1) ✓; ambiguous-tie → hold (Task 1 `_standings`/`_r32_slots` return None → no pairing → Task 3 holds) ✓.
- **Placeholder scan:** no TBD/TODO; every code step is complete; the one adaptive note (Task 1 Step 4 margin perturbation) gives the exact alternative formula, not a vague instruction.
- **Signature consistency:** `resolve_ko_pairings(results_log)→{m:frozenset}`, `_standings(g_obs)→(pos,thirds)|(None,None)`, `_r32_slots(g_obs)→slots|None`, `map_ko_event(parsed, log)→(matchno, winner)|None`, `eligible_ko_targets(parsed, log, now, maturity_hours=3)→(ko_targets, holds)`, `Decision(...).ko_targets`, `decide(...)` returns group+ko. Used identically across tasks. KO keys are strings (match `results_log["ko"]`). `parse_scoreboard` `winner` field added once (Task 2) and consumed in Tasks 2/3/6.
- **Risk flagged:** Task 7 is the only validation against real bracket data (impossible to capture pre-group-stage); the synthetic-fixture tests cover the logic until then.
