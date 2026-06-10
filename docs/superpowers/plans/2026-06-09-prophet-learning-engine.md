# Prophet — Learning Engine (Plan 2 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) tracking.
> **No git:** "Checkpoint" = run the test suite green (no commits).

**Goal:** Turn a match's observed performance (`lambda_obs` from Plan 1) into a bounded, regularized update of each team's Elo strength — the Track B "learning" engine — leaving Track A (frozen) untouched.

**Architecture:** One module `scripts/learn.py`. Three pure functions plus a small stateful class. `lambda_expected(r_home, r_away)` maps two ratings to expected goals using the project's existing Elo→prob→λ model (reuses `poisson_model.fit_rates`). `net_surprise(...)` is the zero-sum "did they out-xG expectation" signal. `update_drift(...)` is the regularized step (decay toward baseline + clipped learning step). `LearningTrack` holds baseline ratings + per-team drift and applies a match symmetrically. The learning rate `k` is the swept knob: `k=0` reproduces the frozen track.

**Tech Stack:** Python 3.10+, pytest, `poisson_model.fit_rates` (existing), math.

**Spec:** `docs/superpowers/specs/2026-06-09-avraa-prophet-living-forecaster-design.md` §6 (the regularized Elo update).

**Math recap (from the spec):**
- `lambda_exp` for each side from current ratings (Elo win-expectancy `e0 = 1/(1+10^(-Δ/400))`, draw term `pd = 0.30·e^(-|Δ|/700)`, then `fit_rates`).
- `surprise_home = (λ_obs_home − λ_exp_home) − (λ_obs_away − λ_exp_away)`; `surprise_away = −surprise_home` (zero-sum, like Elo).
- `drift_new = decay·drift_old + clip(k·surprise, −bound, +bound)`; `rating = baseline + drift`.

---

### Task 1: `lambda_expected` — ratings → expected goals

**Files:**
- Create: `scripts/learn.py`
- Test: `tests/test_learn.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_learn.py`:

```python
from learn import lambda_expected

def test_equal_ratings_give_symmetric_lambdas():
    lh, la = lambda_expected(1800, 1800)
    assert abs(lh - la) < 1e-6
    assert 0.8 < lh < 2.0          # sane international goal rate

def test_stronger_team_has_higher_expected_goals():
    lh, la = lambda_expected(2000, 1700)
    assert lh > la

def test_weaker_home_has_lower_expected_goals():
    lh, la = lambda_expected(1600, 1900)
    assert lh < la
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_learn.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'learn'`.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/learn.py`:

```python
"""Track B learning engine: turn observed performance (lambda_obs) into a
bounded, regularized update of each team's Elo strength. k=0 reproduces the
frozen track. Reuses the project's existing Elo->prob->lambda model."""
import math

from poisson_model import fit_rates


def lambda_expected(r_home, r_away):
    """Two ratings -> (lam_home, lam_away) expected goals, via the same Elo
    win-expectancy + draw model the backtest uses, then fit_rates."""
    d = r_home - r_away
    e0 = 1.0 / (1.0 + 10 ** (-d / 400.0))
    pd = 0.30 * math.exp(-abs(d) / 700.0)
    ph = max(0.01, e0 - pd / 2.0)
    pa = max(0.01, 1.0 - ph - pd)
    s = ph + pd + pa
    return fit_rates(ph / s, pd / s, pa / s)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_learn.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: all green (Plan 1's 11 unit + these 3).

---

### Task 2: `net_surprise` + `update_drift` — the regularized step

**Files:**
- Modify: `scripts/learn.py` (append two functions)
- Test: `tests/test_learn.py` (append tests)

- [ ] **Step 1: Write the failing tests (append)**

Append to `tests/test_learn.py`:

```python
from learn import net_surprise, update_drift

def test_overperformance_is_positive_surprise():
    # generated 2.0 xG (expected 1.0), conceded 0.5 (expected 1.0)
    # (2-1) - (0.5-1) = 1 - (-0.5) = 1.5
    assert net_surprise(2.0, 1.0, 0.5, 1.0) == 1.5

def test_surprise_zero_when_as_expected():
    assert net_surprise(1.2, 1.2, 0.9, 0.9) == 0.0

def test_underperformance_is_negative_surprise():
    assert net_surprise(0.3, 1.0, 1.8, 1.0) == pytest.approx(-1.5)

def test_k_zero_means_only_decay():
    assert update_drift(40.0, 1.5, k=0.0, decay=0.95, bound=75.0) == 38.0  # 0.95*40

def test_step_is_decayed_drift_plus_k_times_surprise():
    # 0.95*10 + 60*0.5 = 9.5 + 30 = 39.5
    assert update_drift(10.0, 0.5, k=60.0, decay=0.95, bound=75.0) == 39.5

def test_step_clipped_to_bound_both_directions():
    assert update_drift(0.0, 5.0, k=60.0, decay=0.95, bound=75.0) == 75.0    # 300 -> 75
    assert update_drift(0.0, -5.0, k=60.0, decay=0.95, bound=75.0) == -75.0  # -300 -> -75
```

Add `import pytest` at the top of `tests/test_learn.py` (needed for `pytest.approx`).

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_learn.py -q`
Expected: FAIL — `ImportError: cannot import name 'net_surprise'`.

- [ ] **Step 3: Implement (append to `scripts/learn.py`)**

```python
def net_surprise(lam_obs_for, lam_exp_for, lam_obs_against, lam_exp_against):
    """Zero-sum performance surprise for the 'for' team: how much it out-xG'd
    expectation in attack, minus how much it leaked in defense."""
    return (lam_obs_for - lam_exp_for) - (lam_obs_against - lam_exp_against)


def update_drift(drift, surprise, k, decay, bound):
    """Regularized online step: decay the accumulated drift toward baseline (0),
    then add the learning step k*surprise, clipped to +/- bound."""
    step = max(-bound, min(bound, k * surprise))
    return decay * drift + step
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_learn.py -q`
Expected: PASS (9 passed).

- [ ] **Step 5: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: all green.

---

### Task 3: `LearningTrack` — per-team drift state, symmetric match update

**Files:**
- Modify: `scripts/learn.py` (append class)
- Test: `tests/test_learn.py` (append tests)

- [ ] **Step 1: Write the failing tests (append)**

Append to `tests/test_learn.py`:

```python
from learn import LearningTrack

def test_k_zero_track_never_moves():
    lt = LearningTrack({"A": 1800, "B": 1700}, k=0.0)
    lt.apply_match("A", "B", lam_obs_home=3.0, lam_obs_away=0.0)
    assert lt.rating("A") == 1800
    assert lt.rating("B") == 1700

def test_dominant_home_raises_home_lowers_away_symmetrically():
    lt = LearningTrack({"A": 1800, "B": 1800}, k=60.0, decay=0.95, bound=75.0)
    lt.apply_match("A", "B", lam_obs_home=3.0, lam_obs_away=0.2)  # A crushed it
    assert lt.rating("A") > 1800
    assert lt.rating("B") < 1800
    # equal start -> drifts are exact negatives (zero-sum)
    assert abs((lt.rating("A") - 1800) + (lt.rating("B") - 1800)) < 1e-9

def test_rating_is_baseline_plus_drift_and_unknown_team_is_baseline():
    lt = LearningTrack({"A": 1800, "B": 1800}, k=60.0)
    lt.apply_match("A", "B", lam_obs_home=2.5, lam_obs_away=0.5)
    assert lt.rating("A") == 1800 + lt.drift["A"]

def test_repeated_dominance_accumulates_but_bounded():
    lt = LearningTrack({"A": 1800, "B": 1800}, k=60.0, decay=0.95, bound=75.0)
    for _ in range(10):
        lt.apply_match("A", "B", lam_obs_home=3.0, lam_obs_away=0.0)
    # drift grows over repeats but the decay caps it below a runaway value
    assert lt.rating("A") - 1800 > 75            # accumulated beyond one game
    assert lt.rating("A") - 1800 < 75 / (1 - 0.95)  # but bounded by step/(1-decay)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_learn.py -q`
Expected: FAIL — `ImportError: cannot import name 'LearningTrack'`.

- [ ] **Step 3: Implement (append to `scripts/learn.py`)**

```python
class LearningTrack:
    """Holds baseline Elo ratings plus a per-team accumulated drift. Each match
    nudges the two teams' drifts symmetrically (zero-sum). The current strength
    of a team is baseline + drift. k is the swept knob (k=0 => frozen track)."""

    def __init__(self, baseline, k=60.0, decay=0.95, bound=75.0):
        self.baseline = dict(baseline)
        self.drift = {t: 0.0 for t in baseline}
        self.k = k
        self.decay = decay
        self.bound = bound

    def rating(self, team):
        return self.baseline[team] + self.drift.get(team, 0.0)

    def apply_match(self, home, away, lam_obs_home, lam_obs_away):
        """Update both teams' drift from one finished match's observed goals."""
        lam_exp_home, lam_exp_away = lambda_expected(self.rating(home),
                                                     self.rating(away))
        s_home = net_surprise(lam_obs_home, lam_exp_home,
                              lam_obs_away, lam_exp_away)
        for team, s in ((home, s_home), (away, -s_home)):
            self.drift[team] = update_drift(self.drift.get(team, 0.0), s,
                                            self.k, self.decay, self.bound)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_learn.py -q`
Expected: PASS (13 passed).

- [ ] **Step 5: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: all green (Plan 1's 11 + Plan 2's 13 = 24 unit tests).

---

## Definition of Done (Plan 2)

- `lambda_expected(r_home, r_away)` returns expected goals via the existing model (unit-tested: symmetry, monotonicity).
- `net_surprise` is the zero-sum attack-minus-defense surprise (unit-tested incl. exact arithmetic).
- `update_drift` is decay + clipped step (unit-tested: k=0, clipping, arithmetic).
- `LearningTrack` holds baseline + drift, applies a match symmetrically; `k=0` reproduces the frozen track (unit-tested: zero-sum, accumulation-but-bounded).
- `python3 -m pytest tests/ -q` green.

**Hands off to Plan 3 (Snapshot + Orchestration + 2022 replay):** `LearningTrack` provides the per-step ratings that Track B feeds into the Monte Carlo re-simulation; `build_performance_record` (Plan 1) provides the `lam_obs_*` inputs to `apply_match`.
