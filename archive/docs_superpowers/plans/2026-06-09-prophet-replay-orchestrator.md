# Prophet — Snapshot + Two-Track Replay Orchestrator (Plan 4 of 5)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox (`- [ ]`) tracking.
> **No git:** "Checkpoint" = run the test suite green.

**Goal:** The machinery that drives both forecast tracks game-by-game and records the trajectory: a KL-divergence "information content" measure and a `run_replay` orchestrator that, for an ordered list of games, re-simulates the *frozen* track (baseline ratings) and the *learning* track (`LearningTrack`-updated ratings), recording each champion distribution and the information each game carried.

**Architecture:** Two small modules. `snapshot.py` holds `kl_divergence(p, q)` (bits) over champion distributions. `replay.py` holds `champion_dist` (extract champion probs from a `simulate` result) and `run_replay`, which threads conditioning + learning through the game sequence and calls `sim_tournament.simulate` for both tracks at each step, emitting a trajectory of snapshots with `kl_from_prev`.

**Tech Stack:** Python 3.10+, pytest, reuse `sim_tournament.simulate`, `learn.LearningTrack`, `math`.

**Spec:** `docs/superpowers/specs/2026-06-09-avraa-prophet-living-forecaster-design.md` §2-3 (two tracks, snapshot trajectory, KL attribution).

**Scope note:** Plan 4 builds and unit-tests the orchestration on a *synthetic* tournament (the free feed is missing 5 of the 2022 knockout games — the penalty shootouts — so the real 2022 data must be hand-assembled). Assembling the real 2022 `structure` + ratings + complete results, running the replay, and the figures/paper section is **Plan 5**. One snapshot per game per track (the post-result forecast) is recorded here; the live-2026 "before-kickoff lineup" snapshot is a later refinement.

**Game contract (input to `run_replay`):** `games` is an ordered list of dicts:
`{"home": str, "away": str, "kind": "group"|"ko", "result": (hg, ag) | winner_name, "lam_obs": {"home": float, "away": float}}` — `result` is a scoreline tuple for group games, the winner's name for knockout games; `lam_obs` is the observed expected-goals from Plan 1.

---

### Task 1: `kl_divergence` — information content in bits

**Files:**
- Create: `scripts/snapshot.py`
- Test: `tests/test_snapshot.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_snapshot.py`:

```python
import pytest
from snapshot import kl_divergence

def test_kl_zero_for_identical_distributions():
    p = {"a": 0.5, "b": 0.3, "c": 0.2}
    assert kl_divergence(p, p) == 0.0

def test_kl_positive_when_different():
    p = {"a": 0.7, "b": 0.3}
    q = {"a": 0.3, "b": 0.7}
    assert kl_divergence(p, q) > 0

def test_kl_one_bit_for_half_mass_move():
    # all mass on 'a' (was 0.5) -> KL = 1*log2(1/0.5) = 1 bit
    p = {"a": 1.0, "b": 0.0}
    q = {"a": 0.5, "b": 0.5}
    assert kl_divergence(p, q) == pytest.approx(1.0)

def test_kl_skips_zero_mass_terms_and_floors_q():
    # b has 0 prob in p -> contributes nothing; a-only term, q floored (no div0)
    p = {"a": 1.0, "b": 0.0}
    q = {"a": 1.0, "b": 0.0}
    assert kl_divergence(p, q) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_snapshot.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'snapshot'`.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/snapshot.py`:

```python
"""Snapshot helpers for the forecast trajectory. kl_divergence measures the
information (in bits) between two champion distributions -- how much a game
moved the forecast."""
import math


def kl_divergence(p, q, eps=1e-12):
    """KL(p || q) in bits over champion distributions {team: prob}. Terms with
    p[t] == 0 contribute nothing; q[t] is floored at eps to avoid div-by-zero."""
    total = 0.0
    for team, pt in p.items():
        if pt > 0:
            qt = max(q.get(team, 0.0), eps)
            total += pt * math.log2(pt / qt)
    return total
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_snapshot.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: all green (35 prior + 4 = 39).

---

### Task 2: `champion_dist` + `run_replay` — the two-track orchestrator

**Files:**
- Create: `scripts/replay.py`
- Test: `tests/test_replay.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_replay.py`:

```python
from replay import run_replay, champion_dist

# synthetic 2 groups of 4 -> top 2 -> 4-team knockout (same shape as the sim tests)
def _structure():
    rr = lambda ts: [(ts[i], ts[j]) for i in range(4) for j in range(i + 1, 4)]
    A = ["A1", "A2", "A3", "A4"]
    B = ["B1", "B2", "B3", "B4"]
    return {"groups": {"A": A, "B": B}, "fixtures": {"A": rr(A), "B": rr(B)},
            "bracket": [("A", 1), ("B", 2), ("B", 1), ("A", 2)]}

def _ratings():
    return {"A1": 2200, "A2": 1750, "A3": 1700, "A4": 1650,
            "B1": 1900, "B2": 1750, "B3": 1700, "B4": 1650}

def test_champion_dist_extracts_probs():
    out = {"X": {"champion": 0.6, "reached": {1: 0.9}},
           "Y": {"champion": 0.4, "reached": {1: 0.8}}}
    assert champion_dist(out) == {"X": 0.6, "Y": 0.4}

def test_replay_has_both_tracks_with_baseline_plus_one_per_game():
    games = [{"home": "A1", "away": "A2", "kind": "group", "result": (1, 0),
              "lam_obs": {"home": 1.5, "away": 0.5}}]
    traj = run_replay(_structure(), _ratings(), games, N=1500, seed=7)
    assert set(traj) == {"frozen", "learning"}
    # one t=0 baseline snapshot + one per game
    assert len(traj["frozen"]) == 2 and len(traj["learning"]) == 2
    for snaps in traj.values():
        for s in snaps:
            assert abs(sum(s["champion"].values()) - 1.0) < 1e-9
            assert "kl_from_prev" in s

def test_big_result_carries_more_information_than_a_calm_one():
    # game 1: bottom seeds draw (little news). game 2: top seed A1 loses (big news)
    games = [
        {"home": "A3", "away": "A4", "kind": "group", "result": (1, 1),
         "lam_obs": {"home": 1.0, "away": 1.0}},
        {"home": "A1", "away": "A2", "kind": "group", "result": (0, 3),
         "lam_obs": {"home": 0.3, "away": 2.5}},
    ]
    traj = run_replay(_structure(), _ratings(), games, N=3000, seed=7)
    kl_calm = traj["frozen"][1]["kl_from_prev"]   # after the A3-A4 draw
    kl_upset = traj["frozen"][2]["kl_from_prev"]  # after A1 loses
    assert kl_upset > kl_calm

def test_learning_diverges_from_frozen_on_a_dominated_winner():
    # A1 wins all three group games 1-0 but is OUT-xG'd every time (lucky wins).
    # Frozen keeps A1 strong (it qualified); learning weakens A1 (poor xG) ->
    # A1's champion prob is lower on the learning track.
    g = lambda opp: {"home": "A1", "away": opp, "kind": "group", "result": (1, 0),
                     "lam_obs": {"home": 0.3, "away": 1.8}}
    games = [g("A2"), g("A3"), g("A4")]
    traj = run_replay(_structure(), _ratings(), games, N=4000, seed=7)
    fz = traj["frozen"][-1]["champion"]["A1"]
    ln = traj["learning"][-1]["champion"]["A1"]
    assert ln < fz
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_replay.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'replay'`.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/replay.py`:

```python
"""Two-track replay orchestrator. Steps an ordered game list, conditioning the
simulation on each result, and emits a champion-distribution trajectory for the
frozen track (baseline ratings) and the learning track (LearningTrack ratings).
Each snapshot carries the KL information content vs the previous snapshot."""
from sim_tournament import simulate
from learn import LearningTrack
from snapshot import kl_divergence


def champion_dist(sim_out):
    """Extract {team: champion_prob} from a sim_tournament.simulate result."""
    return {t: sim_out[t]["champion"] for t in sim_out}


def _snapshot(traj, prev, name, index, home, away, dist):
    kl = kl_divergence(dist, prev[name]) if prev[name] is not None else 0.0
    traj[name].append({"game_index": index, "home": home, "away": away,
                       "champion": dist, "kl_from_prev": kl})
    prev[name] = dist


def run_replay(structure, baseline, games, N=4000, seed=2026):
    """games: ordered list of {home, away, kind, result, lam_obs}. Returns
    {"frozen": [snap...], "learning": [snap...]} with a t=0 baseline snapshot
    (game_index -1) plus one snapshot per game on each track."""
    groups, ko = {}, {}
    learn = LearningTrack(baseline)
    traj = {"frozen": [], "learning": []}
    prev = {"frozen": None, "learning": None}

    # t=0 baseline (no games conditioned; learning == baseline)
    base_dist = champion_dist(simulate(structure, baseline, {}, {}, N, seed))
    for name in ("frozen", "learning"):
        _snapshot(traj, prev, name, -1, None, None, dict(base_dist))

    for i, g in enumerate(games):
        if g["kind"] == "group":
            groups[(g["home"], g["away"])] = g["result"]
        else:
            ko[(g["home"], g["away"])] = g["result"]
        learn.apply_match(g["home"], g["away"],
                          g["lam_obs"]["home"], g["lam_obs"]["away"])
        learn_ratings = {t: learn.rating(t) for t in baseline}
        for name, ratings in (("frozen", baseline), ("learning", learn_ratings)):
            dist = champion_dist(simulate(structure, ratings, groups, ko, N, seed))
            _snapshot(traj, prev, name, i, g["home"], g["away"], dist)
    return traj
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_replay.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Checkpoint**

Run: `python3 -m pytest tests/ -q`
Expected: all green (43 total).

---

## Definition of Done (Plan 4)

- `kl_divergence` — information in bits between champion distributions (tested: zero, positive, 1-bit case, zero-mass/flooring).
- `champion_dist` — extracts champion probs (tested).
- `run_replay` — two-track trajectory with t=0 baseline + per-game snapshots; champion mass sums to 1; uneven information (upset > calm); learning diverges from frozen on a dominated winner (all tested on synthetic).
- `python3 -m pytest tests/ -q` green (43 unit tests).

**Hands off to Plan 5 (real 2022 data + run + figures + paper):** assemble the real 2022 `structure` + Nov-2022 ratings + complete results (group results from the free tool; the 5 penalty-shootout knockouts hardcoded), build the `games` list (with `lam_obs` from Plan 1's `build_performance_record`), call `run_replay`, then plot the A-vs-B champion trajectory + the KL attribution and write the "Learning as the Tournament Speaks" paper section.
