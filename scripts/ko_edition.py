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
from realistic_scores import KO_TIES

DATA = Path(__file__).resolve().parent.parent / "data"
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
