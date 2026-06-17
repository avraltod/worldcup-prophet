"""The live 2026 Learning-track state: baseline Elo(+injury adj) ratings, a
per-team drift updated from each match's lambda_obs, the per-match processed
records (lam_obs vs lam_exp for the paper's performance analysis), and a queue
of matches whose box scores are not yet available. Locked knobs k=50,
decay=0.95, bound=75 (paper App D.6)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from learn import LearningTrack, lambda_expected
from performance import compute_lambda_obs

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "data" / "learning_state_2026.json"
K, DECAY, BOUND = 50.0, 0.95, 75.0


def baseline_2026():
    # Flat ELO + injury adj, NO host bonus: matches the 2018/2022 replay
    # convention the k-sweep was tuned on; host advantage is left for drift.
    import condition as cond
    return {t: cond.ELO[t] + cond.ADJ.get(t, 0) for t in cond.ELO}


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"k": K, "decay": DECAY, "bound": BOUND,
            "baseline": baseline_2026(), "drift": {},
            "processed": [], "pending": [], "history": []}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1))


def load_live_inputs():
    """Load data/live_inputs.json. Returns {} if file absent (graceful degradation)."""
    p = ROOT / "data" / "live_inputs.json"
    return json.loads(p.read_text()) if p.exists() else {}


def build_eff_elo(state, live):
    """Track B effective ratings: live_elo + live_injury_adj + lineup_adj + drift.

    NO explicit host bonus: like baseline_2026, host advantage is left for the
    learning track to capture through drift (a host out-performing at home shows
    up as positive xG surprise). Adding an explicit host here would double-count
    it. Falls back to raw june10_elo (not state["baseline"]) for teams absent from
    live_elo, because baseline already includes june10_adj — using baseline + inj
    would double-count. Drift (proxy xG signal) is added on top; it captures shot
    quality not in ClubElo.
    """
    from condition import ADJ as june10_adj, ELO as june10_elo
    live_elo = live.get("live_elo", {})
    live_inj = live.get("live_injury_adj")   # None means "key absent" → use june10 fallback
    lineup_adj = live.get("lineup_adj", {})
    drift = state.get("drift", {})
    out = {}
    for t in state["baseline"]:
        base = live_elo.get(t, june10_elo[t])
        if live_inj is None:
            inj = june10_adj.get(t, 0)
        else:
            inj = live_inj.get(t, 0)
        out[t] = base + inj + lineup_adj.get(t, 0) + drift.get(t, 0)
    return out


def _track(state):
    lt = LearningTrack(state["baseline"], k=state["k"],
                       decay=state["decay"], bound=state["bound"])
    lt.drift.update(state["drift"])
    return lt


def ratings(state):
    return {t: state["baseline"][t] + state["drift"].get(t, 0.0)
            for t in state["baseline"]}


def apply_match(state, match, home, away, stats):
    """One finished match -> drift update + processed record. Idempotent:
    a match already in processed returns (state, None) unchanged."""
    if any(r["match"] == match for r in state["processed"]):
        return state, None
    lam = compute_lambda_obs(stats)
    lt = _track(state)
    exp_h, exp_a = lambda_expected(lt.rating(home), lt.rating(away))
    lt.apply_match(home, away, lam["home"], lam["away"])
    state["drift"] = {t: d for t, d in lt.drift.items() if d}
    rec = {"match": match, "home": home, "away": away,
           "lam_obs": {"home": round(lam["home"], 3),
                       "away": round(lam["away"], 3), "source": lam["source"]},
           "lam_exp": {"home": round(exp_h, 3), "away": round(exp_a, 3)},
           "drift_after": {home: round(state["drift"].get(home, 0.0), 2),
                           away: round(state["drift"].get(away, 0.0), 2)}}
    state["processed"].append(rec)
    state["pending"] = [m for m in state["pending"] if m != match]
    return state, rec


def sync(state, entries, stats_lookup):
    """Process every documented match in order; queue the ones whose stats are
    unavailable (stats_lookup(match) -> stats dict or None)."""
    done = {r["match"] for r in state["processed"]}
    for e in sorted(entries, key=lambda e: e["match"]):
        m = e["match"]
        if m in done:
            continue
        home, away = e["fixture"].split(" v ")
        stats = stats_lookup(m)
        if stats is None:
            if m not in state["pending"]:
                state["pending"].append(m)
            continue
        state, _ = apply_match(state, m, home, away, stats)
    return state
