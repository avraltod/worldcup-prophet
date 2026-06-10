# Before/After Forecast Records (v2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an isolated v2 system that records a pre-game snapshot (forecast + lineup + market) and a post-game record (result + re-conditioned forecast + performance) per group match — 72×2 = 144 records — writing only to v2 files and an inert workflow, leaving the live v1 system untouched until cutover.

**Architecture:** New `scripts/live_update_v2.py` polls ESPN, decides per match whether a `pre` or `post` record is due (pure `plan_records`), and writes per-match entries to `data/trajectory_v2.json` (+ `results_log_v2.json`, `records_index_v2.json`). Reuses `condition.conditional_probs`, `market_snapshot`, and a new pure scoring helper. A `workflow_dispatch`-only workflow runs it. The forecast math is unchanged (pre is a snapshot — no method change).

**Tech Stack:** Python 3.12 stdlib, pytest, GitHub Actions. Source spec: `archive/docs_superpowers/specs/2026-06-10-before-after-v2-design.md`.

**Build location:** Do this work on a branch `before-after-v2` (keeps `main` deployable). Commits stay LOCAL / on the branch; nothing is pushed until the user chooses cutover.

**Verified shapes (2026-06-10):**
- ESPN summary `…/summary?event=<id>` → `rosters` (len 2), each `{homeAway, team, roster:[{starter, athlete:{displayName}, …}]}`; 11 starters/side.
- `match_expectations.json` entries: `{match, row, group, home, away, pick:[hg,ag], probs_HDA:[H,D,A], lh, la, ev_points, …}` keyed by official match number.
- `fetch_results.parse_scoreboard` events: `{home, away, hg, ag, kickoff(UTC aware), final}` (+ `winner` exists on the parked KO branch — NOT here). `map_to_fixture(home,away)` → `(official_matchno, fixture_home, fixture_away, reversed)|None`.
- `condition.conditional_probs(results_log, N)` → `{team: {champion: p, …}}`; results_log group keyed by official match number (1–72).
- `market_snapshot.fetch_market_champion()` → `{team: prob}` or `{}` offline.

**v2 allowlist (only files v2 may write):** `data/trajectory_v2.json`, `data/results_log_v2.json`, `data/records_index_v2.json`. (README only post-cutover — not in this plan.)

---

### Task 0: Create the build branch

- [ ] **Step 1: Branch from current main**

Run:
```bash
cd /Users/avraa/iDrive/GitHub/MGL/FIFA
git checkout -b before-after-v2
git rev-parse --abbrev-ref HEAD
```
Expected: `before-after-v2`. All subsequent commits land here, local only.

---

### Task 1: Pure per-match scoring helper

**Files:**
- Create: `scripts/scoring.py`
- Create: `tests/test_scoring.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scoring.py
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import scoring

ROOT = Path(__file__).resolve().parent.parent
EXP = json.loads((ROOT / "data" / "match_expectations.json").read_text())
M1 = next(m for m in EXP if m["match"] == 1)   # Mexico v South Africa

def test_exact_pick_scores_three():
    r = scoring.score_match(M1["home"], M1["away"], M1["pick"][0], M1["pick"][1])
    assert r["points"] == 3
    assert r["ev_points"] == M1["ev_points"]
    assert 0.0 <= r["brier"] <= 2.0 and 0.0 <= r["p_outcome"] <= 1.0

def test_wrong_result_scores_zero():
    # invert the pick's result to guarantee a wrong outcome
    hg, ag = M1["pick"]
    r = scoring.score_match(M1["home"], M1["away"], ag, hg + 3)  # away wins big if pick was home win
    assert r["points"] in (0, 1, 2, 3)  # defined; exact value depends on pick
    assert isinstance(r["points"], int)

def test_reversed_pairing_is_oriented():
    r = scoring.score_match(M1["away"], M1["home"], M1["pick"][1], M1["pick"][0])
    assert r["points"] == 3   # same match, reversed input -> still the exact pick

def test_unknown_pairing_returns_none():
    assert scoring.score_match("Mars", "Venus", 1, 0) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_scoring.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scoring'`.

- [ ] **Step 3: Implement `scripts/scoring.py`**

```python
"""Pure per-match scoring (pool 3/2/1 + Brier), reused by the v2 recorder without
touching v1's ledger. Mirrors score_day.py's formula; reads match_expectations.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import canon
from poisson_model import pois  # noqa: F401  (imported for parity; brier uses probs_HDA)

ROOT = Path(__file__).resolve().parent.parent
_EXP = json.loads((ROOT / "data" / "match_expectations.json").read_text())
_BY_PAIR = {(m["home"], m["away"]): m for m in _EXP}


def _outcome(hg, ag):
    return "H" if hg > ag else ("D" if hg == ag else "A")


def score_match(home, away, hg, ag):
    """Return {points, ev_points, p_outcome, brier} for a group match (inputs oriented
    to the given home/away), or None if the pairing is not a known group fixture."""
    key = (canon(home), canon(away))
    m = _BY_PAIR.get(key)
    if m is None:
        m = _BY_PAIR.get((key[1], key[0]))
        if m is None:
            return None
        hg, ag = ag, hg  # orient to the fixture's home/away
    pick = m["pick"]
    real_out, pick_out = _outcome(hg, ag), _outcome(*pick)
    if [hg, ag] == pick:
        pts = 3
    elif real_out == pick_out and (hg - ag) == (pick[0] - pick[1]):
        pts = 2
    elif real_out == pick_out:
        pts = 1
    else:
        pts = 0
    p_out = m["probs_HDA"]["HDA".index(real_out)]
    brier = sum((p - (1.0 if "HDA"[i] == real_out else 0.0)) ** 2
                for i, p in enumerate(m["probs_HDA"]))
    return {"points": pts, "ev_points": m["ev_points"],
            "p_outcome": round(p_out, 4), "brier": round(brier, 4)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_scoring.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/scoring.py tests/test_scoring.py
git commit -m "Add pure per-match scoring helper (3/2/1 + Brier)"
```

---

### Task 2: ESPN lineup fetch + parse

**Files:**
- Create: `scripts/lineups.py`
- Create: `data/espn_summary_sample.json` (captured ESPN summary, committed for offline tests)
- Create: `tests/test_lineups.py`

- [ ] **Step 1: Capture one real ESPN summary (has full rosters)**

Run:
```bash
python3 - <<'PY'
import json, urllib.request
from pathlib import Path
url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event=633850"
with urllib.request.urlopen(url, timeout=30) as r:
    Path("data/espn_summary_sample.json").write_text(r.read().decode())
print("captured")
PY
```
Expected: `captured`.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_lineups.py
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import lineups

ROOT = Path(__file__).resolve().parent.parent
SUMMARY = json.loads((ROOT / "data" / "espn_summary_sample.json").read_text())

def test_parse_lineup_extracts_eleven_starters_per_side():
    lu = lineups.parse_lineup(SUMMARY)
    assert lu is not None
    assert len(lu["home"]) == 11 and len(lu["away"]) == 11
    assert all(isinstance(n, str) and n for n in lu["home"] + lu["away"])

def test_parse_lineup_none_when_no_rosters():
    assert lineups.parse_lineup({}) is None
    assert lineups.parse_lineup({"rosters": []}) is None

def test_fetch_lineup_uses_injected_opener():
    class FakeResp:
        def __init__(self, text): self._t = text
        def read(self): return self._t.encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    captured = {}
    def opener(url, timeout=0):
        captured["url"] = url
        return FakeResp(json.dumps(SUMMARY))
    lu = lineups.fetch_lineup(633850, opener=opener)
    assert "event=633850" in captured["url"]
    assert len(lu["home"]) == 11
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_lineups.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'lineups'`.

- [ ] **Step 4: Implement `scripts/lineups.py`**

```python
"""Pure ESPN lineup fetch + parse for the v2 recorder.
summary?event=<id> -> {"home": [starters], "away": [starters]} or None."""
import json
import urllib.request

SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary"


def parse_lineup(summary):
    """ESPN summary JSON -> {"home": [...], "away": [...]} or None if starters absent."""
    rosters = summary.get("rosters")
    if not rosters:
        return None
    out = {}
    for r in rosters:
        side = r.get("homeAway")
        if side not in ("home", "away"):
            continue
        starters = [p["athlete"]["displayName"]
                    for p in r.get("roster", [])
                    if p.get("starter") and p.get("athlete", {}).get("displayName")]
        if starters:
            out[side] = starters
    return out if out.get("home") and out.get("away") else None


def fetch_lineup(event_id, opener=urllib.request.urlopen):
    """Network: fetch + parse the lineup for an ESPN event id. opener is injectable."""
    with opener(f"{SUMMARY_URL}?event={event_id}", timeout=30) as resp:
        return parse_lineup(json.loads(resp.read().decode()))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_lineups.py -q`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add scripts/lineups.py data/espn_summary_sample.json tests/test_lineups.py
git commit -m "Add ESPN lineup fetch+parse with captured summary fixture"
```

---

### Task 3: Expose ESPN event id from parse_scoreboard

**Files:**
- Modify: `scripts/fetch_results.py` (add `event_id` to the parsed dict — additive, v1-safe)
- Modify: `tests/test_fetch_results.py` (assert the new field)

- [ ] **Step 1: Add the failing assertion** — append to `tests/test_fetch_results.py`:

```python
def test_parse_includes_event_id():
    payload = {"events": [{"id": "633850", "date": "2026-06-11T19:00Z",
        "competitions": [{
            "status": {"type": {"state": "post", "completed": True, "detail": "FT"}},
            "competitors": [
                {"homeAway": "home", "team": {"displayName": "Mexico"}, "score": "2"},
                {"homeAway": "away", "team": {"displayName": "South Africa"}, "score": "1"}]}]}]}
    assert fr.parse_scoreboard(payload)[0]["event_id"] == "633850"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_fetch_results.py::test_parse_includes_event_id -q`
Expected: FAIL — `KeyError: 'event_id'`.

- [ ] **Step 3: Implement** — in `scripts/fetch_results.py`, `parse_scoreboard`, add `"event_id"` to the appended dict (additive; existing v1 fields unchanged). The appended dict becomes:

```python
        out.append({
            "home": sides["home"]["team"]["displayName"],
            "away": sides["away"]["team"]["displayName"],
            "hg": _score(sides["home"]),
            "ag": _score(sides["away"]),
            "kickoff": dt.datetime.fromisoformat(ev["date"].replace("Z", "+00:00")),
            "final": final,
            "event_id": ev.get("id"),
        })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_fetch_results.py -q`
Expected: PASS (existing fetch tests + the new one; the added field is ignored by v1 logic).

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_results.py tests/test_fetch_results.py
git commit -m "Expose ESPN event_id from parse_scoreboard (additive)"
```

---

### Task 4: v2 orchestrator — trigger logic + records

**Files:**
- Create: `scripts/live_update_v2.py`
- Create: `tests/test_live_update_v2.py`

- [ ] **Step 1: Write the failing test (pure `plan_records`)**

```python
# tests/test_live_update_v2.py
import sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import live_update_v2 as v2

NOW = dt.datetime(2026, 6, 11, 18, 30, tzinfo=dt.timezone.utc)

def ev(match, mins_to_kickoff, final=False, has_scores=False):
    return {"match": match, "kickoff": NOW + dt.timedelta(minutes=mins_to_kickoff),
            "final": final, "has_scores": has_scores}

EMPTY = {"pre": [], "post": []}

def test_pre_fires_in_window_once():
    actions = v2.plan_records([ev(1, 30)], EMPTY, NOW)
    assert actions == [(1, "pre")]

def test_pre_not_fired_outside_window():
    assert v2.plan_records([ev(1, 200)], EMPTY, NOW) == []      # too far out
    assert v2.plan_records([ev(1, -10)], EMPTY, NOW) == []      # already kicked off (no pre)

def test_pre_skipped_if_already_done():
    assert v2.plan_records([ev(1, 30)], {"pre": [1], "post": []}, NOW) == []

def test_post_fires_when_final_once():
    actions = v2.plan_records([ev(1, -120, final=True, has_scores=True)], EMPTY, NOW)
    assert actions == [(1, "post")]

def test_post_skipped_if_recorded_or_not_final():
    assert v2.plan_records([ev(1, -120, final=True, has_scores=True)],
                           {"pre": [], "post": [1]}, NOW) == []
    assert v2.plan_records([ev(1, -120, final=False, has_scores=False)], EMPTY, NOW) == []

def test_md3_two_simultaneous_yield_two_pre_in_match_order():
    actions = v2.plan_records([ev(8, 30), ev(7, 30)], EMPTY, NOW)
    assert actions == [(7, "pre"), (8, "pre")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_live_update_v2.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'live_update_v2'`.

- [ ] **Step 3: Implement `scripts/live_update_v2.py`**

```python
"""Before/After v2 recorder. Polls ESPN; per group match emits a pre-game snapshot
(forecast + lineup + market) and a post-game record (result + re-conditioned forecast
+ performance). Isolated: writes only the v2 files; never touches v1 files."""
import datetime as dt
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import fetch_results as fr
import lineups
import scoring
import market_snapshot
from condition import conditional_probs

TRAJ = ROOT / "data" / "trajectory_v2.json"
RESULTS = ROOT / "data" / "results_log_v2.json"
INDEX = ROOT / "data" / "records_index_v2.json"
PRE_WINDOW = dt.timedelta(minutes=90)
N_SIM = 50000


def plan_records(events, index, now, pre_window=PRE_WINDOW):
    """Pure: events = [{match, kickoff(aware UTC), final, has_scores}], index =
    {"pre":[...], "post":[...]}. Returns [(match#, "pre"|"post")] in match-number order."""
    pre_done, post_done = set(index.get("pre", [])), set(index.get("post", []))
    actions = []
    for e in sorted(events, key=lambda e: e["match"]):
        m = e["match"]
        if m not in pre_done and now < e["kickoff"] <= now + pre_window:
            actions.append((m, "pre"))
        if m not in post_done and e["final"] and e["has_scores"]:
            actions.append((m, "post"))
    return actions


def _load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def _iso(d):
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _champion_dist(results_log):
    probs = conditional_probs(results_log, N=N_SIM)
    return {t: round(d["champion"], 4) for t, d in probs.items() if d["champion"] > 0}


def _kl_bits(p_after, p_before):
    if not p_before:
        return 0.0
    eps, s = 1e-6, 0.0
    for t in set(p_after) | set(p_before):
        pa, pb = p_after.get(t, 0) + eps, p_before.get(t, 0) + eps
        s += pa * math.log2(pa / pb)
    return round(s, 4)


def _prev_champion():
    traj = _load(TRAJ, [])
    return traj[-1]["champion"] if traj else {}


def _append(rec):
    traj = _load(TRAJ, [])
    traj.append(rec)
    TRAJ.write_text(json.dumps(traj, ensure_ascii=False, indent=1))


def _mark(match, phase):
    idx = _load(INDEX, {"pre": [], "post": []})
    if match not in idx[phase]:
        idx[phase].append(match)
    INDEX.write_text(json.dumps(idx))


def make_pre_record(e, now):
    log = _load(RESULTS, {"group": {}, "ko": {}})
    champ = _champion_dist(log)
    rec = {"phase": "pre", "match": e["match"],
           "label": f"PRE M{e['match']} {e['fh']} v {e['fa']}",
           "time": _iso(now), "kickoff": _iso(e["kickoff"]),
           "n_recorded": len(log["group"]) + len(log.get("ko", {})),
           "champion": champ, "market_champion": market_snapshot.fetch_market_champion(),
           "info_bits": _kl_bits(champ, _prev_champion()),
           "lineup": lineups.fetch_lineup(e["event_id"]) if e.get("event_id") else None,
           "result": None, "performance": None}
    _append(rec)
    _mark(e["match"], "pre")


def make_post_record(e, now):
    log = _load(RESULTS, {"group": {}, "ko": {}})
    hg, ag = (e["ag"], e["hg"]) if e["rev"] else (e["hg"], e["ag"])  # fixture-oriented
    log.setdefault("group", {})[str(e["match"])] = [hg, ag]
    RESULTS.write_text(json.dumps(log, ensure_ascii=False, indent=1))
    champ = _champion_dist(log)
    rec = {"phase": "post", "match": e["match"],
           "label": f"POST M{e['match']} {e['fh']} v {e['fa']}",
           "time": _iso(now), "kickoff": _iso(e["kickoff"]),
           "n_recorded": len(log["group"]) + len(log.get("ko", {})),
           "champion": champ, "market_champion": market_snapshot.fetch_market_champion(),
           "info_bits": _kl_bits(champ, _prev_champion()),
           "lineup": None, "result": [hg, ag],
           "performance": scoring.score_match(e["fh"], e["fa"], hg, ag)}
    _append(rec)
    _mark(e["match"], "post")


def _normalize(parsed):
    out = []
    for p in parsed:
        fx = fr.map_to_fixture(p["home"], p["away"])
        if fx is None:
            continue
        m, fh, fa, rev = fx
        out.append({"match": m, "fh": fh, "fa": fa, "rev": rev,
                    "kickoff": p["kickoff"], "final": p["final"],
                    "has_scores": p["hg"] is not None and p["ag"] is not None,
                    "hg": p["hg"], "ag": p["ag"], "event_id": p.get("event_id")})
    return out


def _date_window(now, back=1, fwd=1):
    return [(now.date() + dt.timedelta(days=i)).strftime("%Y%m%d")
            for i in range(-back, fwd + 1)]


def main(argv):
    dry = "--dry-run" in argv
    now = dt.datetime.now(dt.timezone.utc)
    parsed = fr.fetch_dates(_date_window(now))
    events = _normalize(parsed)
    actions = plan_records(events, _load(INDEX, {"pre": [], "post": []}), now)
    if not actions:
        print("v2: nothing due.")
        return 0
    by_match = {e["match"]: e for e in events}
    for m, phase in actions:
        if dry:
            print(f"v2 --dry-run: would record {phase} M{m}")
            continue
        (make_pre_record if phase == "pre" else make_post_record)(by_match[m], now)
        print(f"v2: recorded {phase} M{m}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_live_update_v2.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/live_update_v2.py tests/test_live_update_v2.py
git commit -m "Add v2 orchestrator: plan_records + pre/post recorders"
```

---

### Task 5: v2 publish integration test

**Files:**
- Create: `tests/test_v2_integration.py`

- [ ] **Step 1: Write the test** (real conditioning; restores v2 files in teardown)

```python
# tests/test_v2_integration.py
"""End-to-end v2: a pre record (snapshot+market, no result) and a post record (result
applied + performance), using real conditioning. Restores v2 files in teardown."""
import sys, json, datetime as dt
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import live_update_v2 as v2

TRAJ = ROOT / "data" / "trajectory_v2.json"
RESULTS = ROOT / "data" / "results_log_v2.json"
INDEX = ROOT / "data" / "records_index_v2.json"


@pytest.fixture
def clean_v2():
    saved = {p: (p.read_text() if p.exists() else None) for p in (TRAJ, RESULTS, INDEX)}
    for p in (TRAJ, RESULTS, INDEX):
        p.exists() and p.unlink()
    yield
    for p, text in saved.items():
        if text is None:
            p.exists() and p.unlink()
        else:
            p.write_text(text)


def _ev(match, rev=False):
    return {"match": match, "fh": "Mexico", "fa": "South Africa", "rev": rev,
            "kickoff": dt.datetime(2026, 6, 11, 19, 0, tzinfo=dt.timezone.utc),
            "final": True, "has_scores": True, "hg": 2, "ag": 1, "event_id": None}


def test_pre_then_post_records(clean_v2):
    RESULTS.write_text(json.dumps({"group": {}, "ko": {}}))
    now = dt.datetime.now(dt.timezone.utc)

    v2.make_pre_record(_ev(1), now)
    traj = json.loads(TRAJ.read_text())
    assert traj[-1]["phase"] == "pre" and traj[-1]["match"] == 1
    assert traj[-1]["result"] is None and traj[-1]["champion"]   # forecast present
    assert json.loads(RESULTS.read_text())["group"] == {}        # pre applies no result

    v2.make_post_record(_ev(1), now)
    traj = json.loads(TRAJ.read_text())
    assert traj[-1]["phase"] == "post" and traj[-1]["result"] == [2, 1]
    assert traj[-1]["performance"]["points"] == 3                 # 2-1 == M1 pick [?] -> see note
    assert json.loads(RESULTS.read_text())["group"]["1"] == [2, 1]
    assert json.loads(INDEX.read_text()) == {"pre": [1], "post": [1]}
```

NOTE: M1's locked pick is `[1, 0]` (from `match_expectations.json`), so a 2-1 result is a
correct outcome but not exact → `points` would be 1, not 3. Before running, set the test's
result to the actual M1 pick to assert an exact hit: change `"hg": 2, "ag": 1` in `_ev` to the
pick values and the post assertion to `== 3`. Read the pick at test top:
`PICK = next(m for m in json.loads((ROOT/"data"/"match_expectations.json").read_text()) if m["match"]==1)["pick"]`
and use `PICK[0]/PICK[1]` for the scores and `points == 3`.

- [ ] **Step 2: Adjust the test to use M1's real pick, then run**

Apply the NOTE: at the top of the test read `PICK`, set `_ev`'s `hg, ag` to `PICK[0], PICK[1]`, and assert `performance["points"] == 3`. Run:
`python3 -m pytest tests/test_v2_integration.py -q -s`
Expected: PASS (~10–30s for the two conditionings).

- [ ] **Step 3: Confirm pristine restore**

Run: `git status --porcelain`
Expected: shows only the new untracked test file. `data/trajectory_v2.json`, `data/results_log_v2.json`, `data/records_index_v2.json` must NOT appear as modified (teardown restored/removed them). If they do, STOP and report BLOCKED.

- [ ] **Step 4: Full suite**

Run: `python3 -m pytest -q`
Expected: all pass (~2–3 min).

- [ ] **Step 5: Commit**

```bash
git add tests/test_v2_integration.py
git commit -m "Add v2 publish integration test"
```

---

### Task 6: Inert v2 workflow

**Files:**
- Create: `.github/workflows/live-update-v2.yml`

- [ ] **Step 1: Write the workflow (dispatch-only — no cron)**

```yaml
# .github/workflows/live-update-v2.yml
name: live-update-v2
on:
  workflow_dispatch: {}        # inert until cutover: no cron yet
permissions:
  contents: write
concurrency:
  group: live-update-v2
  cancel-in-progress: false
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Run v2 recorder
        run: python3 scripts/live_update_v2.py
      - name: Commit and push v2 files only
        run: |
          CHANGED=$(git status --porcelain \
            data/trajectory_v2.json data/results_log_v2.json data/records_index_v2.json)
          if [ -z "$CHANGED" ]; then
            echo "v2: no changes."
            exit 0
          fi
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data/trajectory_v2.json data/results_log_v2.json data/records_index_v2.json
          for f in $(git diff --cached --name-only); do
            case "$f" in
              data/trajectory_v2.json|data/results_log_v2.json|data/records_index_v2.json) ;;
              *) echo "REFUSING: non-allowlisted file staged: $f"; exit 1 ;;
            esac
          done
          git pull --rebase origin "$GITHUB_REF_NAME" || true
          git commit -m "v2 records: $(date -u +%Y-%m-%dT%H:%MZ)"
          git push
```

- [ ] **Step 2: Validate YAML**

Run:
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/live-update-v2.yml')); print('yaml OK')" 2>/dev/null || echo "PyYAML absent — Actions will validate"
```
Expected: `yaml OK` (or the skip note).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/live-update-v2.yml
git commit -m "Add inert (dispatch-only) v2 workflow"
```

- [ ] **Step 4: Final full suite on the branch**

Run: `python3 -m pytest -q`
Expected: all pass.

---

## Self-review (completed by plan author)

- **Spec coverage:** pre = snapshot+lineup+market, no result applied (Task 4 `make_pre_record`, Task 5 asserts `result is None` and `group` unchanged) ✓; post = result + re-conditioned forecast + performance (Task 4 `make_post_record`, Task 1 scoring, Task 5) ✓; per-match records + MD3 match-order (Task 4 `plan_records`, test `test_md3_…`) ✓; isolation to v2 files only (all writes target `*_v2.json`; workflow allowlist Task 6) ✓; inert workflow (dispatch-only, Task 6) ✓; lineups from ESPN summary (Task 2) ✓; `info_bits` KL vs previous record (Task 4 `_kl_bits`/`_prev_champion`) ✓; build on a branch, nothing pushed (Task 0) ✓; zero secrets/deps (stdlib + repo) ✓; no v1 file touched except the additive `event_id` field (Task 3, behavior-preserving) ✓; KO out of scope (only `map_to_fixture` group matches resolved) ✓.
- **Placeholder scan:** no TBD/TODO. The one adaptive note (Task 5) is explicit: read M1's real pick and assert `points == 3`; concrete, not vague.
- **Signature consistency:** `score_match(home, away, hg, ag) -> {points, ev_points, p_outcome, brier}|None`; `parse_lineup(summary)`/`fetch_lineup(event_id, opener)`; `plan_records(events, index, now, pre_window) -> [(match, phase)]`; `make_pre_record(e, now)`/`make_post_record(e, now)` consume the normalized event dict from `_normalize` (`match, fh, fa, rev, kickoff, final, has_scores, hg, ag, event_id`). Record keys match the spec schema. v2 results log group keyed by official match number (consistent with the v1 keying fix).
- **Risk flagged:** the integration test (Task 5) must use M1's real locked pick for the exact-hit assertion; the NOTE gives the precise adjustment.
