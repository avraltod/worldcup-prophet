"""Run the 2022 World Cup group-stage replay (Plan 5): pull real group results +
performance (lambda_obs) from the free feed, then run the two-track replay
(frozen vs learning) and save the champion-probability trajectory.

  python3 scripts/run_2022_replay.py --games-only   # build+cache the games (network)
  python3 scripts/run_2022_replay.py --N 1000       # run the replay (compute)
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from tournament_2022 import GROUPS, BRACKET, RATINGS, TEAM_GROUP
from collect_match import build_performance_record
from replay import run_replay

GAMES_CACHE = ROOT / "data" / "replay_2022_games.json"
TRAJ_OUT = ROOT / "data" / "replay_2022_trajectory.json"
SEASON = "world-cup-2022"


def _cli(*args):
    return json.loads(subprocess.run(
        ["sports-skills", "football", *args],
        capture_output=True, text=True, timeout=90).stdout)


def build_games():
    """The 48 group games (both teams in the same group), schedule order, with
    result + lambda_obs (real stats; fall back to actual goals if stats missing)."""
    sched = _cli("get_season_schedule", f"--season_id={SEASON}")
    games = []
    seen = set()                          # first occurrence only: the 3rd-place
    for m in sched["data"]["schedules"]:  # playoff repeats a same-group pairing
        if m.get("status") != "closed":
            continue
        comp = {c["qualifier"]: c["team"]["name"] for c in m["competitors"]}
        home, away = comp.get("home"), comp.get("away")
        if home not in TEAM_GROUP or away not in TEAM_GROUP:
            continue
        if TEAM_GROUP[home] != TEAM_GROUP[away]:
            continue   # cross-group -> knockout game, skip
        pair = frozenset((home, away))
        if pair in seen:
            continue   # repeated pairing (e.g. third-place playoff) -> skip
        seen.add(pair)
        hg, ag = m["scores"]["home"], m["scores"]["away"]
        try:
            rec = build_performance_record(m["id"], home, away)
            lam = {"home": rec["lambda_obs"]["home"], "away": rec["lambda_obs"]["away"]}
            src = rec["lambda_obs"]["source"]
        except Exception:
            lam = {"home": float(hg), "away": float(ag)}
            src = "goals_fallback"
        games.append({"home": home, "away": away, "kind": "group",
                      "result": [hg, ag], "lam_obs": lam, "source": src})
    return games


def load_games():
    if GAMES_CACHE.exists():
        return json.loads(GAMES_CACHE.read_text())
    games = build_games()
    GAMES_CACHE.write_text(json.dumps(games, indent=2))
    return games


def main(N=1500, seed=2022):
    games = load_games()
    print(f"{len(games)} group games loaded "
          f"({sum(1 for g in games if g['source'] == 'goals_fallback')} on goals-fallback)")
    for g in games:                       # JSON lists -> tuples
        g["result"] = tuple(g["result"])
    structure = {"groups": GROUPS,
                 "fixtures": {grp: [] for grp in GROUPS},
                 "bracket": BRACKET}
    for g in games:
        structure["fixtures"][TEAM_GROUP[g["home"]]].append((g["home"], g["away"]))
    nfix = [len(f) for f in structure["fixtures"].values()]
    print(f"fixtures per group: {nfix} (each should be 6)")
    traj = run_replay(structure, RATINGS, games, N=N, seed=seed)
    TRAJ_OUT.write_text(json.dumps(traj, indent=2))
    print(f"trajectory saved -> {TRAJ_OUT} "
          f"({len(traj['frozen'])} snapshots per track)")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--N", type=int, default=1500)
    p.add_argument("--games-only", action="store_true")
    a = p.parse_args()
    if a.games_only:
        g = load_games()
        print(f"cached {len(g)} games -> {GAMES_CACHE}")
    else:
        main(N=a.N)
