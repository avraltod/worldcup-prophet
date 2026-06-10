"""Held-out validation + controls for the learning study, answering the peer
review's two CRITICAL issues:
 (1) leave-one-tournament-out cross-validation — tune k on one World Cup, test on
     the OTHER (genuinely out-of-sample);
 (2) a placebo control — shuffle the xG signal across games and re-run: if the
     finalist lift is the *signal* (not just a free parameter), it must collapse;
 (3) proxy stability across tournaments + calibration RMSE vs a naive baseline.
"""
import json
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from replay import run_replay
import tournament_2018 as T18
import tournament_2022 as T22

ROOT = Path(__file__).parent.parent
COEF = json.loads((ROOT / "data" / "proxy_coef.json").read_text())["sot"]


def load(mod, cache):
    games = json.loads((ROOT / "data" / cache).read_text())
    for g in games:
        g["result"] = tuple(g["result"])
    S = {"groups": mod.GROUPS, "fixtures": {x: [] for x in mod.GROUPS}, "bracket": mod.BRACKET}
    for g in games:
        S["fixtures"][mod.TEAM_GROUP[g["home"]]].append((g["home"], g["away"]))
    return games, S, mod.RATINGS


g22, S22, R22 = load(T22, "replay_2022_games.json")
g18, S18, R18 = load(T18, "replay_2018_games.json")
FIN22, FIN18 = ["Argentina", "France"], ["France", "Croatia"]
CH22, CH18 = "Argentina", "France"


def run(S, R, games, k, N=4000, seed=7):
    tr = run_replay(S, R, games, N=N, seed=seed, k=k)
    return tr["frozen"][-1]["champion"], tr["learning"][-1]["champion"]


print("=== (1) Leave-one-tournament-out cross-validation (k tuned on the OTHER WC) ===")
for tag, (S, R, gms, fin, ch, k_train) in [
        ("train 2018 (k=60) -> TEST 2022", (S22, R22, g22, FIN22, CH22, 60)),
        ("train 2022 (k=40) -> TEST 2018", (S18, R18, g18, FIN18, CH18, 40))]:
    fz, ln = run(S, R, gms, k_train)
    flift = (sum(ln[t] for t in fin) - sum(fz[t] for t in fin)) * 100
    llf = -math.log(max(fz[ch], 1e-9)); lll = -math.log(max(ln[ch], 1e-9))
    print(f"  {tag}: finalist lift {flift:+.1f} pts | champ log-loss {llf:.3f} -> {lll:.3f} ({'better' if lll < llf else 'worse'})")

print("\n=== (2) Placebo control: shuffle the xG signal across games (k=50) ===")
for tag, (S, R, gms, fin) in [("2022", (S22, R22, g22, FIN22)), ("2018", (S18, R18, g18, FIN18))]:
    fz, ln = run(S, R, gms, k=50, N=3000)
    real = (sum(ln[t] for t in fin) - sum(fz[t] for t in fin)) * 100
    shuffled = []
    for s in range(4):
        rng = random.Random(s)
        lams = [g["lam_obs"] for g in gms]
        rng.shuffle(lams)
        gsh = [{**g, "lam_obs": lams[i]} for i, g in enumerate(gms)]
        fzs, lns = run(S, R, gsh, k=50, N=3000)
        shuffled.append((sum(lns[t] for t in fin) - sum(fzs[t] for t in fin)) * 100)
    print(f"  {tag}: REAL xG lift {real:+.1f} pts  vs  SHUFFLED-xG lift {statistics.mean(shuffled):+.1f} +/- {statistics.pstdev(shuffled):.1f} (4 shuffles)")

print("\n=== (3) Proxy stability + calibration ===")


def rows(games):
    out = []
    for g in games:
        out.append((g["lam_obs"]["home"] / COEF, g["result"][0]))
        out.append((g["lam_obs"]["away"] / COEF, g["result"][1]))
    return out


def fit_c(rs):
    return sum(s * go for s, go in rs) / sum(s * s for s, _ in rs)


def rmse(rs, c):
    return math.sqrt(sum((c * s - go) ** 2 for s, go in rs) / len(rs))


r18, r22 = rows(g18), rows(g22)
c18, c22 = fit_c(r18), fit_c(r22)
print(f"  proxy coef fit on 2018 alone: {c18:.3f} | on 2022 alone: {c22:.3f} | combined (locked): {COEF:.3f}")
print(f"  cross-tournament goal-RMSE: fit-2018->predict-2022 {rmse(r22, c18):.3f} | fit-2022->predict-2018 {rmse(r18, c22):.3f}")
for tag, rs in [("2018", r18), ("2022", r22)]:
    mean_g = sum(go for _, go in rs) / len(rs)
    naive = math.sqrt(sum((mean_g - go) ** 2 for _, go in rs) / len(rs))
    print(f"  {tag}: proxy RMSE {rmse(rs, COEF):.3f} vs naive-mean RMSE {naive:.3f}  (proxy {'beats' if rmse(rs, COEF) < naive else 'loses to'} naive)")
