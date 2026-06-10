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
    # de-dup on (phase, match): a crash between _append and _mark must not yield a
    # duplicate trajectory entry when plan_records retries the record next run.
    if any(r.get("phase") == rec["phase"] and r.get("match") == rec["match"] for r in traj):
        return
    traj.append(rec)
    TRAJ.write_text(json.dumps(traj, ensure_ascii=False, indent=1))


def _mark(match, phase):
    idx = _load(INDEX, {"pre": [], "post": []})
    idx.setdefault(phase, [])
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
