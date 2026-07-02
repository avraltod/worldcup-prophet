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
import live_state as lst

TRAJ = ROOT / "data" / "trajectory_v2.json"
RESULTS = ROOT / "data" / "results_log_v2.json"
INDEX = ROOT / "data" / "records_index_v2.json"
PRE_WINDOW = dt.timedelta(minutes=90)
N_SIM = 50000

# ESPN status detail -> how the game was decided. FT (and anything unexpected)
# means the result stood at 90'; AET/Pens mean it went beyond regulation, so the
# stored final score is NOT the 90' scoreline.
_DECIDED = {"FT": "reg", "AET": "et", "Pens": "pens"}


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


def _champion_dist_b(results_log):
    """Track B champion distribution using full current information from live_inputs.json."""
    live = lst.load_live_inputs()
    if not live.get("live_elo") and not live.get("live_rates"):
        return {}
    state = lst.load_state()
    eff_elo = lst.build_eff_elo(state, live)
    live_rates = {int(k): v for k, v in live.get("live_rates", {}).items()}
    probs = conditional_probs(results_log, N=N_SIM,
                              ratings=eff_elo, live_rates=live_rates or None)
    return {t: round(d["champion"], 4) for t, d in probs.items() if d["champion"] > 0}


def _info_snapshot():
    """Extract provenance summary from live_inputs.json. Returns {} if file absent."""
    live = lst.load_live_inputs()
    if not live:
        return {}
    summary = live.get("deltas", {}).get("summary", {})
    return {
        "fetched_at": live.get("fetched_at"),
        **live.get("source_freshness", {}),
        **summary,
    }


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
           "event_id": e.get("event_id"),
           "lineup": lineups.fetch_lineup(e["event_id"]) if e.get("event_id") else None,
           "result": None, "performance": None}
    rec["champion_b"] = _champion_dist_b(log)
    rec["info_snapshot"] = _info_snapshot()
    _append(rec)
    _mark(e["match"], "pre")


def _apply_result(log, e):
    """Write one finalized result into the results log. A knockout match (>72)
    records the advancing team in log['ko'] (what the conditioning needs); a
    group match records the fixture-oriented 90' scoreline in log['group']."""
    if e["match"] > 72:
        log.setdefault("ko", {})[str(e["match"])] = e["winner"]
    else:
        hg, ag = (e["ag"], e["hg"]) if e["rev"] else (e["hg"], e["ag"])
        log.setdefault("group", {})[str(e["match"])] = [hg, ag]
    return log


def make_post_record(e, now):
    log = _load(RESULTS, {"group": {}, "ko": {}})
    hg, ag = (e["ag"], e["hg"]) if e["rev"] else (e["hg"], e["ag"])  # fixture-oriented
    is_ko = e["match"] > 72
    decided = e.get("decided", "reg")
    _apply_result(log, e)
    RESULTS.write_text(json.dumps(log, ensure_ascii=False, indent=1))
    champ = _champion_dist(log)
    # A knockout game that reached extra time or penalties was level at 90'; ESPN
    # gives only the ET-inclusive final score, NOT the 90' scoreline the pool grades.
    # Hold the regulation score (record only the advancer) until it is confirmed.
    reg_pending = is_ko and decided != "reg"
    rec = {"phase": "post", "match": e["match"],
           "label": f"POST M{e['match']} {e['fh']} v {e['fa']}",
           "time": _iso(now), "kickoff": _iso(e["kickoff"]),
           "n_recorded": len(log["group"]) + len(log.get("ko", {})),
           "champion": champ, "market_champion": market_snapshot.fetch_market_champion(),
           "info_bits": _kl_bits(champ, _prev_champion()),
           "lineup": None, "result": None if reg_pending else [hg, ag],
           "winner": e.get("winner"),
           "performance": None if is_ko else scoring.score_match(e["fh"], e["fa"], hg, ag)}
    if is_ko:
        rec["decided"] = decided
    if reg_pending:
        rec["reg_score_pending"] = True
    rec["champion_b"] = _champion_dist_b(log)
    rec["info_snapshot"] = _info_snapshot()
    _append(rec)
    _mark(e["match"], "post")


def _normalize(parsed, results_log=None):
    out = []
    for p in parsed:
        fx = fr.map_to_fixture(p["home"], p["away"])
        is_ko = False
        if fx is None and results_log is not None:        # not a group fixture: try the KO bracket
            fx = fr.ko_fixture(p["home"], p["away"], results_log)
            is_ko = fx is not None
        if fx is None:
            continue
        m, fh, fa, rev = fx
        # group: final when ESPN reports full time. knockout: final once the game
        # is completed (FT/AET/penalties) and ESPN has flagged the advancer.
        final = (p["completed"] and p.get("winner") is not None) if is_ko else p["final"]
        out.append({"match": m, "fh": fh, "fa": fa, "rev": rev,
                    "kickoff": p["kickoff"], "final": final,
                    "has_scores": p["hg"] is not None and p["ag"] is not None,
                    "hg": p["hg"], "ag": p["ag"], "event_id": p.get("event_id"),
                    "is_ko": is_ko, "winner": p.get("winner"),
                    "decided": _DECIDED.get(p.get("detail"), "reg")})
    return out


def _date_window(now, back=1, fwd=1):
    return [(now.date() + dt.timedelta(days=i)).strftime("%Y%m%d")
            for i in range(-back, fwd + 1)]


def backfill_lineups():
    """Patch null lineups in pre-records whenever ESPN now has them.
    Uses the event_id stored in the record — no date-window dependency."""
    traj = _load(TRAJ, [])
    patched = 0
    for rec in traj:
        if rec.get("phase") != "pre" or rec.get("lineup") is not None:
            continue
        eid = rec.get("event_id")
        if not eid:
            continue
        lu = lineups.fetch_lineup(eid)
        if lu:
            rec["lineup"] = lu
            patched += 1
            print(f"v2: backfilled lineup for pre M{rec['match']}")
    if patched:
        TRAJ.write_text(json.dumps(traj, ensure_ascii=False, indent=1))
    return patched


def main(argv):
    dry = "--dry-run" in argv
    now = dt.datetime.now(dt.timezone.utc)
    parsed = fr.fetch_dates(_date_window(now))
    events = _normalize(parsed, _load(RESULTS, {"group": {}, "ko": {}}))
    actions = plan_records(events, _load(INDEX, {"pre": [], "post": []}), now)
    if not actions:
        print("v2: nothing due.")
        if not dry:
            backfill_lineups()
        return 0
    by_match = {e["match"]: e for e in events}
    for m, phase in actions:
        if dry:
            print(f"v2 --dry-run: would record {phase} M{m}")
            continue
        (make_pre_record if phase == "pre" else make_post_record)(by_match[m], now)
        print(f"v2: recorded {phase} M{m}")
    if not dry:
        backfill_lineups()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
