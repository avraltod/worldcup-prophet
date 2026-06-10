# Prophet — Match Data & Performance Layer (Plan 1 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Note on commits:** this project is NOT under git. Every "Commit" in the standard
> template is replaced here by a **Checkpoint** step: run the full test suite green.
> (If you `git init` later, convert checkpoints to commits — plain messages, no co-author trailer.)

**Goal:** Turn any finished match into a clean performance record carrying `lambda_obs` — the expected-goals signal that drives the learning engine — built from free data, with real-xG enrichment and graceful proxy fallback.

**Architecture:** Three focused modules. `collect_match.py` pulls a match box-score from the free football data tool and normalizes it to numeric home/away stats. `performance.py` converts shot stats into `lambda_obs` via a proxy calibrated on 2018+2022 World Cups, preferring real xG when available. `fetch_xg.py` is the best-effort free real-xG hook that returns `None` (never raises) so callers fall back to the proxy. A one-time `calibrate_proxy.py` fits the proxy coefficients.

**Tech Stack:** Python 3.10+, pytest 7.4, the `sports-skills` football CLI (free, no key), numpy.

**Spec:** `docs/superpowers/specs/2026-06-09-avraa-prophet-living-forecaster-design.md` (§4 data layer, §6 step 2 the λ_obs input).

---

### Task 1: Test harness setup

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/conftest.py`

- [ ] **Step 1: Create the empty package marker**

Create `tests/__init__.py` with no content (empty file).

- [ ] **Step 2: Add conftest so `import` finds `scripts/`**

Create `tests/conftest.py`:

```python
import sys
from pathlib import Path

# make scripts/ importable as top-level modules in tests
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
```

- [ ] **Step 3: Verify pytest collects nothing yet (no error)**

Run: `python3 -m pytest tests/ -q`
Expected: `no tests ran` (exit 5) — confirms collection works without import errors.

- [ ] **Step 4: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: no errors (no tests yet is fine).

---

### Task 2: `parse_statistics` — normalize a box-score (pure function)

**Files:**
- Create: `scripts/collect_match.py`
- Test: `tests/test_collect_match.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_collect_match.py`:

```python
from collect_match import parse_statistics

# real shape from get_event_statistics (2022 WC match 633790), away made-up but valid
RAW = {
    "status": True,
    "data": {"teams": [
        {"team": {"name": "Qatar"}, "qualifier": "home",
         "statistics": {"ball_possession": "47.1", "shots_total": "0",
            "shots_on_target": "0", "shots_off_target": "0", "shots_blocked": "0",
            "corner_kicks": "1", "fouls": "15", "offsides": "3",
            "yellow_cards": "4", "red_cards": "0", "passes_total": "434"}},
        {"team": {"name": "Ecuador"}, "qualifier": "away",
         "statistics": {"ball_possession": "52.9", "shots_total": "6",
            "shots_on_target": "3", "shots_off_target": "2", "shots_blocked": "1",
            "corner_kicks": "5", "fouls": "11", "offsides": "1",
            "yellow_cards": "2", "red_cards": "0", "passes_total": "500"}},
    ]},
}

def test_parse_converts_strings_to_numbers_and_keys():
    out = parse_statistics(RAW)
    assert out["home"]["team"] == "Qatar"
    assert out["home"]["possession"] == 47.1      # float kept
    assert out["home"]["shots"] == 0              # int
    assert out["away"]["sot"] == 3
    assert out["away"]["corners"] == 5

def test_other_shots_is_offtarget_plus_blocked():
    out = parse_statistics(RAW)
    assert out["away"]["other_shots"] == 3        # 2 off-target + 1 blocked
    assert out["home"]["other_shots"] == 0

def test_missing_or_empty_value_becomes_zero():
    raw = {"data": {"teams": [
        {"team": {"name": "X"}, "qualifier": "home",
         "statistics": {"shots_on_target": "", "shots_total": "4"}},
        {"team": {"name": "Y"}, "qualifier": "away", "statistics": {}},
    ]}}
    out = parse_statistics(raw)
    assert out["home"]["sot"] == 0
    assert out["away"]["shots"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_collect_match.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'collect_match'`.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/collect_match.py`:

```python
"""Pull a finished match box-score from the free football data tool and
normalize it into clean numeric home/away stats."""
import json
import subprocess

# raw stat key -> clean name (only the fields we use downstream)
_KEEP = {
    "ball_possession": "possession",
    "shots_total": "shots",
    "shots_on_target": "sot",
    "shots_off_target": "off_target",
    "shots_blocked": "blocked",
    "corner_kicks": "corners",
    "fouls": "fouls",
    "offsides": "offsides",
    "yellow_cards": "yellow",
    "red_cards": "red",
    "passes_total": "passes",
}


def _num(s):
    """'47.1' -> 47.1, '5' -> 5 (int), '' or None -> 0."""
    if s in (None, ""):
        return 0
    f = float(s)
    return int(f) if f.is_integer() else f


def parse_statistics(raw):
    """raw = JSON dict from get_event_statistics.
    Returns {'home': {clean stats}, 'away': {...}}; adds derived 'other_shots'."""
    out = {}
    for team in raw["data"]["teams"]:
        side = team["qualifier"]                 # 'home' | 'away'
        st = team.get("statistics", {})
        clean = {name: _num(st.get(key)) for key, name in _KEEP.items()}
        clean["team"] = team["team"]["name"]
        clean["other_shots"] = clean["off_target"] + clean["blocked"]
        out[side] = clean
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_collect_match.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: all green.

---

### Task 3: `proxy_xg` — the poor-man's xG formula (pure function)

**Files:**
- Create: `scripts/performance.py`
- Test: `tests/test_performance.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_performance.py`:

```python
from performance import proxy_xg

COEF = {"sot": 0.30, "other": 0.03}   # explicit coef so the test is deterministic

def test_proxy_is_linear_in_shots():
    # 3 on target, 4 other -> 0.9 + 0.12 = 1.02
    assert round(proxy_xg(3, 4, COEF), 4) == 1.02

def test_proxy_zero_when_no_shots():
    assert proxy_xg(0, 0, COEF) == 0.0

def test_proxy_never_negative():
    assert proxy_xg(0, 0, {"sot": -1, "other": -1}) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_performance.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'performance'`.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/performance.py`:

```python
"""Convert a match's shot stats into lambda_obs (expected-goals signal)."""
import json
from pathlib import Path

_COEF_PATH = Path(__file__).parent.parent / "data" / "proxy_coef.json"


def load_coef():
    """Calibrated proxy coefficients (written by calibrate_proxy.py)."""
    return json.loads(_COEF_PATH.read_text())


def proxy_xg(sot, other_shots, coef=None):
    """Poor-man's xG: c_sot * SoT + c_other * other_shots, floored at 0."""
    c = coef if coef is not None else load_coef()
    return max(0.0, c["sot"] * sot + c["other"] * other_shots)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_performance.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: all green.

---

### Task 4: `calibrate_proxy.py` — fit the proxy on 2018+2022 World Cups

**Files:**
- Create: `scripts/calibrate_proxy.py`
- Create (output): `data/proxy_coef.json`

This is a one-time integration script (network + fit). It iterates the 2018 and 2022
World Cup schedules, pulls each match's shot stats and actual goals, and fits
`goals ≈ c_sot·SoT + c_other·other_shots` by non-negative least squares.

- [ ] **Step 1: Write the script**

Create `scripts/calibrate_proxy.py`:

```python
"""One-time: fit proxy-xG coefficients (goals ~ a*SoT + b*other_shots) on the
2018 + 2022 World Cups, using only free data. Writes data/proxy_coef.json."""
import json
import subprocess
from pathlib import Path

import numpy as np
from collect_match import parse_statistics

SEASONS = ["world-cup-2018", "world-cup-2022"]
OUT = Path(__file__).parent.parent / "data" / "proxy_coef.json"


def _cli(*args):
    return json.loads(subprocess.run(
        ["sports-skills", "football", *args],
        capture_output=True, text=True, timeout=90).stdout)


def _matches(season):
    sched = _cli("get_season_schedule", f"--season_id={season}")
    return sched["data"]["schedules"]


def _goals(match):
    """(home_goals, away_goals) from a match's scores block.
    Verified shape (2022 WC): {'home': 0, 'away': 2} — plain integers."""
    sc = match.get("scores") or {}
    h, a = sc.get("home"), sc.get("away")
    if h is None or a is None:
        return None, None
    return int(h), int(a)


def collect_rows():
    """Return rows of (sot, other_shots, goals) — one per team per match."""
    rows = []
    for season in SEASONS:
        for m in _matches(season):
            if m.get("status") != "closed":
                continue
            hg, ag = _goals(m)
            if hg is None or ag is None:
                continue
            try:
                stats = parse_statistics(
                    _cli("get_event_statistics", f"--event_id={m['id']}"))
            except Exception:
                continue
            if "home" not in stats or "away" not in stats:
                continue
            rows.append((stats["home"]["sot"], stats["home"]["other_shots"], hg))
            rows.append((stats["away"]["sot"], stats["away"]["other_shots"], ag))
    return rows


def fit(rows):
    """Non-negative least squares of goals on [SoT, other_shots]."""
    A = np.array([[r[0], r[1]] for r in rows], dtype=float)
    y = np.array([r[2] for r in rows], dtype=float)
    # closed-form OLS then clip to non-negative (simple, dependency-light)
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return {"sot": max(0.0, float(coef[0])), "other": max(0.0, float(coef[1]))}


if __name__ == "__main__":
    rows = collect_rows()
    coef = fit(rows)
    coef["n_team_matches"] = len(rows)
    OUT.write_text(json.dumps(coef, indent=2))
    print(f"fit on {len(rows)} team-matches -> {coef}")
```

- [ ] **Step 2: Run the calibration (network; ~2-4 min for ~256 stat calls)**

Run: `python3 scripts/calibrate_proxy.py`
Expected: prints something like `fit on ~250 team-matches -> {'sot': 0.2x, 'other': 0.0x, ...}` and creates `data/proxy_coef.json`.

- [ ] **Step 3: Sanity-check the coefficients**

Run: `python3 -c "import json; c=json.load(open('data/proxy_coef.json')); print(c); assert c['sot']>c['other']>=0 and 0.15<c['sot']<0.5, 'coefficients out of sane range'"`
Expected: prints the coef dict, no AssertionError. (SoT must matter more than off-target shots; SoT coefficient roughly 0.2–0.4 — about right for "≈1 in 3–4 shots on target is a goal".)

- [ ] **Step 4: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: all green (existing tests unaffected).

---

### Task 5: `fetch_real_xg` — best-effort free xG with a safe-None contract

**Files:**
- Create: `scripts/fetch_xg.py`
- Test: `tests/test_fetch_xg.py`

The robust contract first: `fetch_real_xg` must **never raise** and must return `None`
when real xG is unavailable, so the pipeline always falls back to the proxy. (Wiring a
live FBref/FotMob scrape is its own task in a later plan; this task locks the contract.)

- [ ] **Step 1: Write the failing test**

Create `tests/test_fetch_xg.py`:

```python
from fetch_xg import fetch_real_xg

def test_returns_none_when_no_source_wired():
    # default: no free source implemented yet -> graceful None, no exception
    assert fetch_real_xg("633790", home="Qatar", away="Ecuador") is None

def test_never_raises_on_bad_input():
    # garbage in -> None, not an exception
    assert fetch_real_xg(None) is None
    assert fetch_real_xg("") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_fetch_xg.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_xg'`.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/fetch_xg.py`:

```python
"""Best-effort FREE real-xG fetch (FotMob / FBref). Contract: returns
{'home': float, 'away': float} when available, else None. NEVER raises —
callers fall back to the shots-based proxy. Free sources only."""


def fetch_real_xg(match_id, home=None, away=None):
    """Try free sources for real xG; return dict or None on any failure."""
    try:
        return _fetch_fotmob(match_id, home, away)
    except Exception:
        return None


def _fetch_fotmob(match_id, home, away):
    # Live free scrape is wired in a later plan (fragile; needs live iteration).
    # Until then, signal "not available" so the proxy is used.
    raise NotImplementedError("real-xG source not wired yet; using proxy")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_fetch_xg.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: all green.

---

### Task 6: `compute_lambda_obs` — blend proxy/real with a source flag

**Files:**
- Modify: `scripts/performance.py` (append function)
- Test: `tests/test_performance.py` (append tests)

- [ ] **Step 1: Write the failing test (append)**

Append to `tests/test_performance.py`:

```python
from performance import compute_lambda_obs

STATS = {
    "home": {"sot": 3, "other_shots": 4},
    "away": {"sot": 1, "other_shots": 2},
}

def test_uses_proxy_when_real_xg_is_none():
    out = compute_lambda_obs(STATS, real_xg=None, coef=COEF)
    assert out["source"] == "proxy"
    assert round(out["home"], 4) == 1.02        # 0.30*3 + 0.03*4
    assert round(out["away"], 4) == 0.36        # 0.30*1 + 0.03*2

def test_prefers_real_xg_when_present():
    out = compute_lambda_obs(STATS, real_xg={"home": 2.1, "away": 0.4}, coef=COEF)
    assert out["source"] == "real"
    assert out["home"] == 2.1 and out["away"] == 0.4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_performance.py -q`
Expected: FAIL — `ImportError: cannot import name 'compute_lambda_obs'`.

- [ ] **Step 3: Implement (append to `scripts/performance.py`)**

Append to `scripts/performance.py`:

```python
def compute_lambda_obs(stats, real_xg=None, coef=None):
    """stats = parse_statistics output. real_xg = {'home','away'} or None.
    Returns {'home': λ, 'away': λ, 'source': 'real'|'proxy'}."""
    if real_xg is not None:
        return {"home": real_xg["home"], "away": real_xg["away"], "source": "real"}
    c = coef if coef is not None else load_coef()
    return {
        "home": proxy_xg(stats["home"]["sot"], stats["home"]["other_shots"], c),
        "away": proxy_xg(stats["away"]["sot"], stats["away"]["other_shots"], c),
        "source": "proxy",
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_performance.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: all green.

---

### Task 7: `build_performance_record` — end-to-end on a real 2022 match

**Files:**
- Modify: `scripts/collect_match.py` (append the network wrapper + record builder)
- Test: `tests/test_integration_perf.py`

- [ ] **Step 1: Implement the network wrapper + record builder (append)**

Append to `scripts/collect_match.py`:

```python
def fetch_match_stats(match_id):
    """Network: call the data tool and return parse_statistics(raw)."""
    raw = subprocess.run(
        ["sports-skills", "football", "get_event_statistics",
         f"--event_id={match_id}"],
        capture_output=True, text=True, timeout=60).stdout
    return parse_statistics(json.loads(raw))


def build_performance_record(match_id, home=None, away=None):
    """Full record for one finished match: stats + lambda_obs (real-xG or proxy)."""
    from performance import compute_lambda_obs   # local import avoids cycle
    from fetch_xg import fetch_real_xg
    stats = fetch_match_stats(match_id)
    real = fetch_real_xg(match_id, home, away)
    lam = compute_lambda_obs(stats, real_xg=real)
    return {"match_id": str(match_id), "stats": stats, "lambda_obs": lam}
```

- [ ] **Step 2: Write the integration test (network, marked slow)**

Create `tests/test_integration_perf.py`:

```python
import pytest
from collect_match import build_performance_record

@pytest.mark.integration
def test_real_2022_match_produces_lambda_obs():
    # 633790 = Qatar vs Ecuador, 2022 WC opener (Ecuador won 2-0)
    rec = build_performance_record("633790", home="Qatar", away="Ecuador")
    assert rec["stats"]["home"]["team"] == "Qatar"
    assert "home" in rec["lambda_obs"] and "away" in rec["lambda_obs"]
    assert rec["lambda_obs"]["source"] == "proxy"     # no real-xG source wired
    # Ecuador (away) attacked more -> higher lambda than Qatar (had 0 shots)
    assert rec["lambda_obs"]["away"] > rec["lambda_obs"]["home"]
```

- [ ] **Step 3: Register the `integration` marker**

Create `pytest.ini` at the repo root (`/Users/avraa/iDrive/GitHub/MGL/FIFA/pytest.ini`):

```ini
[pytest]
markers =
    integration: tests that hit the live free data tool (network)
```

- [ ] **Step 4: Run the integration test (network)**

Run: `python3 -m pytest tests/test_integration_perf.py -m integration -q`
Expected: PASS (1 passed) — confirms the whole chain works on a real match and the proxy gives Ecuador a higher λ than shotless Qatar.

- [ ] **Step 5: Checkpoint — full suite (unit only)**

Run: `python3 -m pytest tests/ -q -m "not integration"`
Expected: all unit tests green. Then once more with integration: `python3 -m pytest tests/ -q`.

---

## Definition of Done (Plan 1)

- `collect_match.parse_statistics` normalizes a real box-score (unit-tested).
- `performance.proxy_xg` + `compute_lambda_obs` produce λ_obs, proxy or real (unit-tested).
- `fetch_xg.fetch_real_xg` returns `None` safely (contract-tested).
- `calibrate_proxy.py` has produced `data/proxy_coef.json` with sane coefficients.
- `build_performance_record(match_id)` returns a full record for a real 2022 match (integration-tested).
- `python3 -m pytest tests/ -q` is green.

**Hands off to Plan 2 (Learning Engine):** `build_performance_record` → λ_obs is the
exact input the regularized-Elo update consumes (spec §6 step 2).
