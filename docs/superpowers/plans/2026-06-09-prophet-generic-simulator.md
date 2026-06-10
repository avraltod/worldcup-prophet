# Prophet — Generic Tournament Simulator (Plan 3 of 5)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox (`- [ ]`) tracking.
> **No git:** "Checkpoint" = run the test suite green.

**Goal:** A format-agnostic Monte Carlo tournament simulator that turns (Elo ratings + played results) into champion and stage-reached probabilities for any group-stage + single-elimination structure — the engine both forecast tracks re-run after every game. Works for 2022, 2026, or any synthetic bracket; replaces the 2026-hardcoded `condition.py` for the experiment.

**Architecture:** One module `scripts/sim_tournament.py`. Knockout ties resolve by Elo win-probability (`win_prob`); unplayed group games simulate scorelines from `lambda_expected` (Plan 2) → Poisson sampling (existing `poisson_model.pois`). A `structure` dict (`groups`, `fixtures`, `bracket`) parameterizes the format; played results condition the sim. Output is per-team `{champion, reached[round]}` probabilities over N runs.

**Tech Stack:** Python 3.10+, pytest, `random`, reuse `learn.lambda_expected`, `poisson_model.pois`, `poisson_model.MAX_G`.

**Spec:** `docs/superpowers/specs/2026-06-09-avraa-prophet-living-forecaster-design.md` §2 (both tracks re-simulate), §6 step 5 (re-simulate with updated ratings).

**Data contracts (passed in; this plan does not gather data):**
- `structure = {"groups": {"A": [t1,t2,t3,t4], ...}, "fixtures": {"A": [(h,a), ...], ...}, "bracket": [(group, pos), ...]}` — `bracket` is a flat list of (group, 1-indexed finishing position) refs in single-elim seeding order; its length is a power of two.
- `ratings = {team: elo_float}`
- `group_results = {(home, away): (hg, ag)}` — played group games.
- `ko_results = {(a, b): winner_name}` — played knockout ties.

---

### Task 1: `win_prob`, `_sample_goals`, `simulate_knockout`

**Files:**
- Create: `scripts/sim_tournament.py`
- Test: `tests/test_sim_tournament.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_sim_tournament.py`:

```python
import random
from sim_tournament import win_prob, simulate_knockout

def test_win_prob_is_half_at_equal_ratings():
    assert win_prob(1800, 1800) == 0.5

def test_win_prob_favors_stronger():
    assert win_prob(2000, 1700) > 0.7
    assert win_prob(1700, 2000) < 0.3

def test_knockout_strongest_seed_wins_most():
    ratings = {"S": 2300, "w1": 1600, "w2": 1600, "w3": 1600}
    seeds = ["S", "w1", "w2", "w3"]            # 4-team bracket
    rng = random.Random(1)
    champs = {}
    for _ in range(3000):
        depth = simulate_knockout(seeds, ratings, {}, rng)
        champ = max(depth, key=depth.get)
        champs[champ] = champs.get(champ, 0) + 1
    assert champs["S"] / 3000 > 0.7           # dominant team wins most

def test_knockout_depth_entrant_is_one_champion_is_rounds_plus_one():
    ratings = {"S": 3000, "w1": 1000, "w2": 1000, "w3": 1000}  # S always wins
    depth = simulate_knockout(["S", "w1", "w2", "w3"], ratings, {}, random.Random(0))
    assert depth["S"] == 3                     # 2 rounds won + 1 = champion depth
    assert depth["w1"] == 1                    # entrant, lost first round

def test_knockout_respects_played_result():
    ratings = {"S": 3000, "x": 1000, "a": 1500, "b": 1500}
    # S would dominate, but we record that x beat S in round 1
    depth = simulate_knockout(["S", "x", "a", "b"], ratings,
                              {("S", "x"): "x"}, random.Random(0))
    assert depth["x"] >= 2                     # x advanced past S
    assert depth["S"] == 1                     # S out in round 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_sim_tournament.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sim_tournament'`.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/sim_tournament.py`:

```python
"""Generic Monte Carlo tournament simulator: a group stage (round-robin) plus a
single-elimination knockout, parameterized by a structure dict + Elo ratings +
played results. Format-agnostic (2022, 2026, or any synthetic bracket). Unplayed
group games are simulated from lambda_expected -> Poisson; knockout ties from Elo
win-probability. Produces per-team champion + stage-reached probabilities."""
import random

from learn import lambda_expected
from poisson_model import pois, MAX_G


def win_prob(r_a, r_b):
    """Elo win probability of A over B (knockout — no draws)."""
    return 1.0 / (1.0 + 10 ** (-(r_a - r_b) / 400.0))


def _sample_goals(lam, rng):
    """Sample a goal count from Poisson(lam) via the project's pmf."""
    r, acc = rng.random(), 0.0
    for k in range(MAX_G + 1):
        acc += pois(k, lam)
        if r <= acc:
            return k
    return MAX_G


def simulate_knockout(seeds, ratings, ko_results, rng):
    """seeds = flat list of teams in bracket order (length a power of two).
    Fold the single-elim tree. Returns {team: depth}: entrants have depth 1,
    each win adds 1, so the champion has depth 1 + n_rounds. Played ties use
    ko_results[(a, b)] = winner (either orientation)."""
    depth = {t: 1 for t in seeds}
    teams = list(seeds)
    while len(teams) > 1:
        nxt = []
        for i in range(0, len(teams), 2):
            a, b = teams[i], teams[i + 1]
            played = ko_results.get((a, b), ko_results.get((b, a)))
            if played in (a, b):
                w = played
            else:
                w = a if rng.random() < win_prob(ratings[a], ratings[b]) else b
            depth[w] += 1
            nxt.append(w)
        teams = nxt
    return depth
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_sim_tournament.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: all green (24 prior + 5 = 29).

---

### Task 2: `group_standings`

**Files:**
- Modify: `scripts/sim_tournament.py` (append)
- Test: `tests/test_sim_tournament.py` (append)

- [ ] **Step 1: Write the failing tests (append)**

Append to `tests/test_sim_tournament.py`:

```python
from sim_tournament import group_standings

def test_standings_deterministic_when_all_results_given():
    teams = ["A", "B", "C", "D"]
    fixtures = [("A", "B"), ("A", "C"), ("A", "D"),
                ("B", "C"), ("B", "D"), ("C", "D")]
    # A wins all, B second, C third, D loses all
    results = {("A", "B"): (2, 0), ("A", "C"): (2, 0), ("A", "D"): (3, 0),
               ("B", "C"): (1, 0), ("B", "D"): (2, 0), ("C", "D"): (1, 0)}
    order = group_standings(teams, fixtures, {}, results, random.Random(0))
    assert order == ["A", "B", "C", "D"]

def test_standings_breaks_ties_on_goal_difference():
    teams = ["A", "B", "C", "D"]
    fixtures = [("A", "B"), ("C", "D"), ("A", "C"), ("B", "D"),
                ("A", "D"), ("B", "C")]
    # A and B both beat C and D and draw each other; A has bigger GD
    results = {("A", "B"): (1, 1), ("C", "D"): (0, 0),
               ("A", "C"): (5, 0), ("B", "D"): (1, 0),
               ("A", "D"): (5, 0), ("B", "C"): (1, 0)}
    order = group_standings(teams, fixtures, {}, results, random.Random(0))
    assert order[0] == "A" and order[1] == "B"   # A ahead of B on GD
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_sim_tournament.py -q`
Expected: FAIL — `ImportError: cannot import name 'group_standings'`.

- [ ] **Step 3: Implement (append to `scripts/sim_tournament.py`)**

```python
def group_standings(teams, fixtures, ratings, results, rng):
    """Rank a group. fixtures = [(home, away), ...]. A pair in results uses its
    (hg, ag); otherwise the scoreline is simulated from ratings. Returns the
    teams ordered by (points, goal difference, goals for), best first."""
    pts = {t: 0 for t in teams}
    gd = {t: 0 for t in teams}
    gf = {t: 0 for t in teams}
    for h, a in fixtures:
        if (h, a) in results:
            hg, ag = results[(h, a)]
        else:
            lh, la = lambda_expected(ratings[h], ratings[a])
            hg, ag = _sample_goals(lh, rng), _sample_goals(la, rng)
        gf[h] += hg
        gf[a] += ag
        gd[h] += hg - ag
        gd[a] += ag - hg
        if hg > ag:
            pts[h] += 3
        elif hg < ag:
            pts[a] += 3
        else:
            pts[h] += 1
            pts[a] += 1
    return sorted(teams, key=lambda t: (pts[t], gd[t], gf[t]), reverse=True)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest tests/test_sim_tournament.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: all green (31 total).

---

### Task 3: `simulate_once` + `simulate` (full Monte Carlo)

**Files:**
- Modify: `scripts/sim_tournament.py` (append)
- Test: `tests/test_sim_tournament.py` (append)

- [ ] **Step 1: Write the failing tests (append)**

Append to `tests/test_sim_tournament.py`:

```python
from sim_tournament import simulate

# synthetic: 2 groups of 4 -> top 2 each -> 4-team knockout
def _structure():
    rr = lambda ts: [(ts[i], ts[j]) for i in range(4) for j in range(i + 1, 4)]
    A = ["A1", "A2", "A3", "A4"]
    B = ["B1", "B2", "B3", "B4"]
    return {
        "groups": {"A": A, "B": B},
        "fixtures": {"A": rr(A), "B": rr(B)},
        # R-of-4 seeding order: (A1 v B2), (B1 v A2) -> winners meet in final
        "bracket": [("A", 1), ("B", 2), ("B", 1), ("A", 2)],
    }

def _ratings():
    return {"A1": 2200, "A2": 1750, "A3": 1700, "A4": 1650,
            "B1": 1900, "B2": 1750, "B3": 1700, "B4": 1650}

def test_simulate_returns_probabilities_for_every_team():
    out = simulate(_structure(), _ratings(), N=2000, seed=7)
    assert set(out) == set(_ratings())
    total_champ = sum(o["champion"] for o in out.values())
    assert abs(total_champ - 1.0) < 1e-9        # champion prob sums to 1
    for o in out.values():
        assert 0.0 <= o["champion"] <= 1.0

def test_strongest_team_is_most_likely_champion():
    out = simulate(_structure(), _ratings(), N=4000, seed=7)
    best = max(out, key=lambda t: out[t]["champion"])
    assert best == "A1"
    assert out["A1"]["champion"] > out["B1"]["champion"]

def test_reached_is_monotone_decreasing_by_round():
    out = simulate(_structure(), _ratings(), N=2000, seed=7)
    r = out["A1"]["reached"]                     # {1: reach semifinal, 2: reach final}
    assert r[1] >= r[2] >= out["A1"]["champion"]

def test_conditioning_on_results_shifts_the_forecast():
    # force A1 to lose all three group games -> it should almost never be champion
    losses = {("A1", "A2"): (0, 3), ("A1", "A3"): (0, 3), ("A1", "A4"): (0, 3)}
    base = simulate(_structure(), _ratings(), N=3000, seed=7)
    cond = simulate(_structure(), _ratings(), group_results=losses, N=3000, seed=7)
    assert cond["A1"]["champion"] < base["A1"]["champion"]
    assert cond["A1"]["champion"] < 0.10
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_sim_tournament.py -q`
Expected: FAIL — `ImportError: cannot import name 'simulate'`.

- [ ] **Step 3: Implement (append to `scripts/sim_tournament.py`)**

```python
def simulate_once(structure, ratings, group_results, ko_results, rng):
    """One Monte Carlo run. Returns {team: depth}: 0 if eliminated in the group
    stage, else 1 + knockout wins (champion = 1 + n_rounds)."""
    standings = {
        g: group_standings(teams, structure["fixtures"][g],
                           ratings, group_results, rng)
        for g, teams in structure["groups"].items()
    }
    seeds = [standings[g][pos - 1] for (g, pos) in structure["bracket"]]
    depth = simulate_knockout(seeds, ratings, ko_results, rng)
    out = {t: 0 for teams in structure["groups"].values() for t in teams}
    out.update(depth)
    return out


def simulate(structure, ratings, group_results=None, ko_results=None,
             N=20000, seed=2026):
    """Run N tournaments. Returns {team: {"champion": p, "reached": {r: p}}}
    where reached[r] is P(reaching knockout round r), r = 1..n_rounds."""
    group_results = group_results or {}
    ko_results = ko_results or {}
    rng = random.Random(seed)
    teams = [t for ts in structure["groups"].values() for t in ts]
    n_rounds = len(structure["bracket"]).bit_length() - 1   # log2(bracket size)
    champ_depth = n_rounds + 1
    champ = {t: 0 for t in teams}
    reached = {t: {r: 0 for r in range(1, n_rounds + 1)} for t in teams}
    for _ in range(N):
        d = simulate_once(structure, ratings, group_results, ko_results, rng)
        for t, depth in d.items():
            if depth == champ_depth:
                champ[t] += 1
            for r in range(1, n_rounds + 1):
                if depth >= r:
                    reached[t][r] += 1
    return {
        t: {"champion": champ[t] / N,
            "reached": {r: reached[t][r] / N for r in range(1, n_rounds + 1)}}
        for t in teams
    }
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest tests/test_sim_tournament.py -q`
Expected: PASS (11 passed).

- [ ] **Step 5: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: all green (35 total).

---

## Definition of Done (Plan 3)

- `win_prob`, `simulate_knockout` — Elo knockout, depth tracking, respects played ties (tested).
- `group_standings` — points/GD/GF ranking, results-or-simulated (tested, deterministic + tie-break).
- `simulate_once` + `simulate` — full MC; champion probs sum to 1, strongest team leads, reached[] monotone, conditioning shifts the forecast (tested).
- `python3 -m pytest tests/ -q` green (35 unit tests).

**Hands off to Plan 4 (2022 data + replay + snapshots + orchestration):** Plan 4 supplies the real 2022 `structure` + ratings, drives `simulate(...)` twice per game (frozen ratings vs `LearningTrack` ratings) to produce the before/after snapshots, and records the KL trajectory.
