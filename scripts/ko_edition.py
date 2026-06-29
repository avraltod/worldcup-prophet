"""Build one knockout edition's analysis object, centered on Frozen 2 and
contrasted with Frozen 1. Post-only when the game has no pre-record (e.g. a
game already finished when live recording was enabled).

NOTE: KO_TIES tuple shape is (num, home, away, winner, host_home_flag,
host_away_flag) — the last two elements are host-bonus flags (0/1), NOT
predicted 90' scorelines. Frozen-1 predicted scores are loaded from
data/ko_scores_321.json instead."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ko_score as ks
import update_after_match as uam
import ko_bracket
from realistic_scores import KO_TIES

DATA = Path(__file__).resolve().parent.parent / "data"
PAPER = Path(__file__).resolve().parent.parent / "paper"
ENTRY_LOG = DATA / "ko_edition_log.json"
_KO_SCORES = json.loads((DATA / "ko_scores_321.json").read_text())

_F1 = {n: {"home": h, "away": a,
            "disp": _KO_SCORES.get(str(n), [0, 0]),
            "advancer": w}
       for (n, h, a, w, *_) in KO_TIES}


def _pts(pick, actual_home, actual_away, actual_90, advancer):
    if pick is None or not ks.applies(pick, actual_home, actual_away):
        return 0, False
    return ks.score_pick(pick, actual_90, advancer), pick["advancer"] == advancer


def build_ko_entry(match, records, frozen2_picks, actual_home, actual_away):
    pre = next((r for r in records if r["phase"] == "pre" and r["match"] == match), None)
    post = next((r for r in records if r["phase"] == "post" and r["match"] == match), None)
    if post is None:
        raise ValueError(f"no post record for match {match}")
    f2 = frozen2_picks.get(str(match))
    actual_90, adv = post["result"], post["winner"]
    f2_pts, f2_hit = _pts(f2, actual_home, actual_away, actual_90, adv)
    f1_pts, _ = _pts(_F1.get(match), actual_home, actual_away, actual_90, adv)
    return {
        "match": match, "home": actual_home, "away": actual_away,
        "result": actual_90, "advancer": adv, "info_bits": post.get("info_bits"),
        "frozen2_pick": f2, "frozen2_points": f2_pts, "frozen2_hit": f2_hit,
        "frozen1_pick": _F1.get(match), "frozen1_points": f1_pts,
        "recond_delta": f2_pts - f1_pts,
        "champion_after": post.get("champion"), "champion_b_after": post.get("champion_b"),
        "pre": None if pre is None else {
            "champion": pre.get("champion"), "champion_b": pre.get("champion_b"),
            "market": pre.get("market_champion")},
        "post_only": pre is None}


def scorecard(entries):
    return {"games": len(entries),
            "frozen2_total": sum(e["frozen2_points"] for e in entries),
            "frozen1_total": sum(e["frozen1_points"] for e in entries),
            "recond_total": sum(e["recond_delta"] for e in entries)}


def _round_name(m):
    if m <= 88: return "Round of 32"
    if m <= 96: return "Round of 16"
    if m <= 100: return "Quarter-final"
    if m in (101, 102): return "Semi-final"
    return "Third-place play-off" if m == 103 else "Final"


def render_unit(entries):
    """LaTeX for the knockout edition unit: the latest game in focus + the running
    Frozen-2 scorecard with the Frozen-2 - Frozen-1 re-conditioning column."""
    sc = scorecard(entries)
    latest = entries[-1]
    L = [r"\subsection*{Latest knockout edition: %s, %s v %s}" % (
            _round_name(latest["match"]), latest["home"], latest["away"]),
         r"\noindent Result %d--%d, %s advanced. Frozen~2 scored %d pool point%s here "
         r"(re-conditioning %+d vs Frozen~1). The result carried %.3f bits." % (
            latest["result"][0], latest["result"][1], latest["advancer"],
            latest["frozen2_points"], "" if latest["frozen2_points"] == 1 else "s",
            latest["recond_delta"], latest.get("info_bits") or 0.0),
         r"", r"\begin{center}\small",
         r"\begin{tabular}{llccc}",
         r"\toprule Match & Tie & F2 pts & F1 pts & F2$-$F1 \\ \midrule"]
    for e in entries:
        L.append(r"%d & %s v %s & %d & %d & %+d \\" % (
            e["match"], e["home"], e["away"], e["frozen2_points"],
            e["frozen1_points"], e["recond_delta"]))
    L += [r"\midrule \textbf{Total} & & \textbf{%d} & \textbf{%d} & \textbf{%+d} \\" % (
            sc["frozen2_total"], sc["frozen1_total"], sc["recond_total"]),
          r"\bottomrule\end{tabular}\end{center}"]
    return "\n".join(L)


def _trajectory():
    return json.loads((DATA / "trajectory_v2.json").read_text())


def _frozen2():
    return json.loads((DATA / "frozen2_entry.json").read_text())["picks"]


def _load_entries():
    return json.loads(ENTRY_LOG.read_text()) if ENTRY_LOG.exists() else []


def _realized_pair(match):
    log = json.loads((DATA / "results_log_v2.json").read_text())
    pair = ko_bracket.resolve_ko_pairings(log).get(match)
    if pair is None:
        raise SystemExit(f"M{match}: realized pair not resolvable yet")
    f2 = _frozen2().get(str(match), {})
    teams = sorted(pair)
    home = f2.get("home") if f2.get("home") in teams else teams[0]
    away = next(t for t in teams if t != home)
    return home, away


def _render_and_archive(match):
    uam.rerender(include_ko=True)               # KO-condition the living layer (writes ko_edition unit)
    dst = DATA.parent / "archive" / "paper_versions" / f"WC2026_paper_KO_M{match:03d}.pdf"
    uam._latexmk(out_path=dst)                   # builds, copies to dst, raises if not produced


def issue(match):
    home, away = _realized_pair(match)
    entry = build_ko_entry(match, _trajectory(), _frozen2(), home, away)
    entries = [e for e in _load_entries() if e["match"] != match] + [entry]
    entries.sort(key=lambda e: e["match"])
    ENTRY_LOG.write_text(json.dumps(entries, ensure_ascii=False, indent=1))
    _render_and_archive(match)
    return entry
