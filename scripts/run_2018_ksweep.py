"""Build the 2018 group-stage replay and run its k-sweep — a second tuning point
to confirm (or challenge) the k=40 default chosen on 2022. 2018 champion: France,
runner-up Croatia. Note: France won its group unconvincingly, so this is a real
test of whether the learning benefit generalises beyond 2022."""
import json
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tournament_2018 import GROUPS, BRACKET, RATINGS, TEAM_GROUP
from collect_match import build_performance_record
from replay import run_replay

ROOT = Path(__file__).parent.parent
CACHE = ROOT / "data" / "replay_2018_games.json"
SEASON = "world-cup-2018"


def _cli(*a):
    return json.loads(subprocess.run(["sports-skills", "football", *a],
                                     capture_output=True, text=True, timeout=90).stdout)


def build_games():
    sched = _cli("get_season_schedule", f"--season_id={SEASON}")
    games, seen = [], set()
    for m in sched["data"]["schedules"]:
        if m.get("status") != "closed":
            continue
        comp = {c["qualifier"]: c["team"]["name"] for c in m["competitors"]}
        h, a = comp.get("home"), comp.get("away")
        if h not in TEAM_GROUP or a not in TEAM_GROUP or TEAM_GROUP[h] != TEAM_GROUP[a]:
            continue
        pair = frozenset((h, a))
        if pair in seen:
            continue
        seen.add(pair)
        hg, ag = m["scores"]["home"], m["scores"]["away"]
        try:
            rec = build_performance_record(m["id"], h, a)
            lam = {"home": rec["lambda_obs"]["home"], "away": rec["lambda_obs"]["away"]}
            src = rec["lambda_obs"]["source"]
        except Exception:
            lam = {"home": float(hg), "away": float(ag)}
            src = "goals_fallback"
        games.append({"home": h, "away": a, "kind": "group",
                      "result": [hg, ag], "lam_obs": lam, "source": src})
    return games


def load_games():
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    g = build_games()
    CACHE.write_text(json.dumps(g, indent=2))
    return g


games = load_games()
for g in games:
    g["result"] = tuple(g["result"])
STRUCT = {"groups": GROUPS, "fixtures": {x: [] for x in GROUPS}, "bracket": BRACKET}
for g in games:
    STRUCT["fixtures"][TEAM_GROUP[g["home"]]].append((g["home"], g["away"]))
print(f"{len(games)} group games   fixtures/group: {[len(f) for f in STRUCT['fixtures'].values()]}")

CHAMP = "France"
FINALISTS = ["France", "Croatia"]
SEMIS = ["France", "Croatia", "Belgium", "England"]
KS = [0, 20, 40, 60, 80, 120, 160, 220, 300]
N = 3000

print(f"\n{'k':>4}  {'P(champ Fra)':>12}  {'P(finalists)':>12}  {'P(semis)':>9}  {'champ log-loss':>14}")
rows = []
for k in KS:
    tr = run_replay(STRUCT, RATINGS, games, N=N, seed=2018, k=k)
    d = tr["learning"][-1]["champion"]
    champ = d[CHAMP]
    fin = sum(d[t] for t in FINALISTS)
    semi = sum(d[t] for t in SEMIS)
    ll = -math.log(max(champ, 1e-9))
    rows.append((k, champ, fin, semi, ll))
    print(f"{k:>4}  {champ*100:>11.1f}%  {fin*100:>11.1f}%  {semi*100:>8.1f}%  {ll:>14.3f}")

best_ll = min(rows, key=lambda r: r[4])
best_semi = max(rows, key=lambda r: r[3])
print(f"\n2018 best by champ (France) log-loss: k={best_ll[0]} "
      f"(log-loss {best_ll[4]:.3f} vs frozen {rows[0][4]:.3f})")
print(f"2018 best by semifinalist mass:       k={best_semi[0]} "
      f"(semis {best_semi[3]*100:.1f}% vs frozen {rows[0][3]*100:.1f}%)")
print("(2022 optimum was k=40 on champion log-loss.)")
