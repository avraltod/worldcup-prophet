"""Knockout round predictor.

Usage: python3 predict_knockout.py ROUND "TeamA|TeamB,TeamC|TeamD,..."
Pairs must be in sheet order (first listed = upper row of the pair).
Emits JSON lines: {"ft": [a, b], "otpk": [x, y] or null, "advance": "Team"}
and an AppleScript to /tmp/fill_<ROUND>.applescript.

Model: current Elo (+ injury adjustments, + host bonus when MEX/USA play at
home venues) -> W/D/L probabilities -> modal FT score conditional on modal
outcome. If modal outcome is a draw, FT is the modal draw score and the
higher-rated team gets +1 in the OT/PK column (sheet adds it when FT is tied).
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fixtures import KNOCKOUT, canon
from poisson_model import modal_score, pois, fit_rates

DATA = Path(__file__).parent.parent / "data"
info = json.loads((DATA / "elo_outright_news.json").read_text())
ELO = {t["team"]: t["elo"] for t in info["elo"]}
ADJ = info["injury_elo_adj"]
HOST_BONUS = {"Mexico": 40, "United States": 40, "Canada": 40}


def rating(team):
    return ELO[team] + ADJ.get(team, 0)


def probs(team_a, team_b, host_a=False, host_b=False):
    ra = rating(team_a) + (HOST_BONUS.get(team_a, 0) if host_a else 0)
    rb = rating(team_b) + (HOST_BONUS.get(team_b, 0) if host_b else 0)
    dr = ra - rb
    e = 1.0 / (1.0 + 10 ** (-dr / 400.0))
    pd = 0.30 * math.exp(-abs(dr) / 700.0)
    ph = max(0.01, e - pd / 2)
    pa = max(0.01, 1.0 - ph - pd)
    s = ph + pd + pa
    return ph / s, pd / s, pa / s


def predict_pair(team_a, team_b, host_a, host_b):
    ph, pd, pa = probs(team_a, team_b, host_a, host_b)
    hg, ag, m = modal_score(ph, pd, pa)
    if hg == ag:  # modal draw -> decide via OT/PK
        adv = team_a if ph >= pa else team_b
        otpk = (1, 0) if adv == team_a else (0, 1)
    else:
        adv = team_a if hg > ag else team_b
        otpk = None
    return {"a": team_a, "b": team_b, "ft": [hg, ag], "otpk": otpk,
            "advance": adv, "p": [round(ph, 3), round(pd, 3), round(pa, 3)]}


def main():
    rnd = sys.argv[1]
    pairs = [p.split("|") for p in sys.argv[2].split(",")]
    hosts_arg = sys.argv[3] if len(sys.argv) > 3 else ""  # e.g. "2a,5b" = pair idx + side at home
    host_flags = set(hosts_arg.split(",")) if hosts_arg else set()
    layout = KNOCKOUT[rnd]
    assert len(pairs) == len(layout["pairs"]), f"need {len(layout['pairs'])} pairs"

    results, lines = [], [
        'tell application "Microsoft Excel"',
        '  set wb to workbook "FIFA_WORLDCUP_2026_ScoreChart_Avraa.xlsx"',
        '  tell worksheet "FIFA2026" of wb']
    for i, ((a, b), (r1, r2)) in enumerate(zip(pairs, layout["pairs"])):
        res = predict_pair(canon(a), canon(b),
                           f"{i}a" in host_flags, f"{i}b" in host_flags)
        results.append(res)
        ft, ot = res["ft"], res["otpk"]
        lines.append(f'    set value of range "{layout["ft"]}{r1}" to {ft[0]}')
        lines.append(f'    set value of range "{layout["ft"]}{r2}" to {ft[1]}')
        if ot:
            lines.append(f'    set value of range "{layout["otpk"]}{r1}" to {ot[0]}')
            lines.append(f'    set value of range "{layout["otpk"]}{r2}" to {ot[1]}')
    lines += ['  end tell', 'end tell']
    Path(f"/tmp/fill_{rnd}.applescript").write_text("\n".join(lines))
    for r in results:
        ot = f' (OT/PK {r["otpk"][0]}-{r["otpk"][1]})' if r["otpk"] else ""
        print(f'{r["a"]:<22} {r["ft"][0]}-{r["ft"][1]}{ot} {r["b"]:<22} '
              f'-> {r["advance"]:<15} p={r["p"]}')
    print(f"\nAppleScript: /tmp/fill_{rnd}.applescript")


if __name__ == "__main__":
    main()
