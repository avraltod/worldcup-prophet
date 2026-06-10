"""Stress-test the live two-track forecaster before the real tournament:
(1) an adversarial scenario battery probing the learning engine + data layer at
their edges, and (2) robustness sweeps checking the headline finding (learning
lifts the eventual finalists) survives seed, rating and proxy perturbations.
Run with the locked default k=40.  ->  python3 scripts/stress_test.py"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tournament_2022 import GROUPS, BRACKET, RATINGS, TEAM_GROUP
from learn import LearningTrack
from performance import compute_lambda_obs
from replay import run_replay

ROOT = Path(__file__).parent.parent
K = 40.0
PASS, FAIL = "PASS", "FAIL"


def chk(cond):
    return PASS if cond else FAIL


# ============================ 1. ADVERSARIAL BATTERY =======================
print("=" * 70)
print("  1. ADVERSARIAL SCENARIOS  (learning engine + data layer at the edges)")
print("=" * 70)

# (a) ugly winner: a strong team is out-xG'd in every game -> must be downgraded
L = LearningTrack({"T": 1900, "O": 1700}, k=K)
for _ in range(3):
    L.apply_match("T", "O", lam_obs_home=0.3, lam_obs_away=1.6)
a = L.rating("T")
print(f"(a) ugly winner (out-xG'd 0.3-1.6 x3):   rating 1900 -> {a:.0f}   [{chk(a < 1900)}]  expect DOWN")

# (b) lucky loser: dominated on xG -> must be upgraded (sees through bad luck)
L = LearningTrack({"T": 1900, "O": 1700}, k=K)
L.apply_match("T", "O", lam_obs_home=2.8, lam_obs_away=0.3)
b = L.rating("T")
print(f"(b) lucky loser (out-xG'd 2.8-0.3):      rating 1900 -> {b:.0f}   [{chk(b > 1900)}]  expect UP")

# (c) red card / 10 men: a sparse box-score must still yield a sane, low lambda
tenman = {"home": {"sot": 1, "other_shots": 2}, "away": {"sot": 6, "other_shots": 5}}
lam_c = compute_lambda_obs(tenman)
ok_c = 0.0 <= lam_c["home"] < 1.0 and lam_c["away"] > lam_c["home"]
print(f"(c) red card / 10 men (1 SoT):           lam_obs={lam_c['home']:.2f} vs {lam_c['away']:.2f}   [{chk(ok_c)}]  sane & low")

# (d) garbage / missing stats: must not crash, must produce a usable lambda
try:
    garbage = {"home": {"sot": 0, "other_shots": 0}, "away": {"sot": 0, "other_shots": 0}}
    lam_d = compute_lambda_obs(garbage)            # all-zero stats
    fallback = compute_lambda_obs(garbage, real_xg=None)  # proxy path
    ok_d = lam_d["source"] == "proxy" and lam_d["home"] == 0.0
except Exception:
    ok_d = False
print(f"(d) garbage / all-zero stats:            lam_obs={lam_d['home']:.2f} (no crash)   [{chk(ok_d)}]")

# (e) extreme blowout: a freak 5.0-0.1 xG game must clip at the +/-75 drift cap
L = LearningTrack({"T": 1900, "O": 1700}, k=K, bound=75.0)
L.apply_match("T", "O", lam_obs_home=5.0, lam_obs_away=0.1)
drift = L.rating("T") - 1900
print(f"(e) extreme blowout (5.0-0.1 xG):        drift {drift:+.0f} of +/-75 cap   [{chk(abs(drift) <= 75.0 + 1e-9)}]  bounded")

# ============================ 2. ROBUSTNESS SWEEPS =========================
print("\n" + "=" * 70)
print("  2. ROBUSTNESS  (does 'learning lifts the eventual finalists' survive?)")
print("=" * 70)

games = json.loads((ROOT / "data" / "replay_2022_games.json").read_text())
STRUCT = {"groups": GROUPS, "fixtures": {g: [] for g in GROUPS}, "bracket": BRACKET}
for g in games:
    STRUCT["fixtures"][TEAM_GROUP[g["home"]]].append((g["home"], g["away"]))
FINALISTS = ["Argentina", "France"]


def finalist_gap(seed=2022, rdelta=None, lam_scale=1.0, N=2500):
    ratings = {t: RATINGS[t] + (rdelta.get(t, 0) if rdelta else 0) for t in RATINGS}
    gms = []
    for g in games:
        gms.append({**g, "result": tuple(g["result"]),
                    "lam_obs": {"home": g["lam_obs"]["home"] * lam_scale,
                                "away": g["lam_obs"]["away"] * lam_scale}})
    tr = run_replay(STRUCT, ratings, gms, N=N, seed=seed, k=K)
    fz = sum(tr["frozen"][-1]["champion"][t] for t in FINALISTS)
    ln = sum(tr["learning"][-1]["champion"][t] for t in FINALISTS)
    return fz, ln


def report(tag, fz, ln):
    g = (ln - fz) * 100
    print(f"  {tag:<34} frozen {fz*100:5.1f}%   learning {ln*100:5.1f}%   gap {g:+5.1f}  [{chk(g > 0)}]")
    return g > 0


gaps_ok = []
print("  -- seed variation --")
for s in (2020, 2021, 2022, 2023):
    gaps_ok.append(report(f"seed {s}", *finalist_gap(seed=s)))
print("  -- baseline-rating perturbation (+/-50 random) --")
for s in (1, 2):
    rng = random.Random(s)
    rd = {t: rng.uniform(-50, 50) for t in RATINGS}
    gaps_ok.append(report(f"ratings jittered (#{s})", *finalist_gap(rdelta=rd)))
print("  -- proxy-xG scale perturbation --")
for sc in (0.8, 1.2):
    gaps_ok.append(report(f"proxy lambda x{sc}", *finalist_gap(lam_scale=sc)))

print("\n" + "-" * 70)
n_ok = sum(gaps_ok)
print(f"  ROBUSTNESS: learning beat frozen in {n_ok}/{len(gaps_ok)} perturbed configurations.")
print("-" * 70)
