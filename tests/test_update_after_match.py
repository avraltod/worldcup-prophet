import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import update_after_match as uam

TRAJ = [
    {"phase": "pre", "match": 1, "kickoff": "2026-06-11T19:00:00Z",
     "champion": {"Spain": 0.2711, "Argentina": 0.1768},
     "market_champion": {"Spain": 0.164}, "info_bits": 0.0,
     "result": None, "performance": None},
    {"phase": "post", "match": 1, "kickoff": "2026-06-11T19:00:00Z",
     "champion": {"Spain": 0.2711, "Argentina": 0.1815}, "info_bits": 0.0011,
     "result": [2, 0],
     "performance": {"points": 1, "ev_points": 0.855, "p_outcome": 0.6718, "brier": 0.1655}},
]
EXP = [{"match": 1, "group": "A", "home": "Mexico", "away": "South Africa",
        "pick": [2, 1], "probs_HDA": [0.6718, 0.2087, 0.1193], "lh": 1.9, "la": 0.65}]

def test_pending_matches_are_finalized_but_undocumented(tmp_path):
    idx = tmp_path / "index.json"
    pending = uam.pending_matches(TRAJ, idx)
    assert pending == [1]

def test_re_ev_delta_uses_ev_pick():
    # realistic pick 2-1 scored 1; EV pick 1-0 also scores 1 vs 2-0 -> delta 0
    d = uam.re_ev_delta_for(EXP[0], [2, 0], realistic_points=1)
    assert d == 0

def test_build_full_entry_attaches_interpretation_and_failure_tag(tmp_path):
    e = uam.build_full_entry(1, TRAJ, EXP, forecast_commit="abc1234",
                             documented_at="2026-06-11T21:10:58Z", use_api=False)
    assert e["interpretation"]                      # non-empty (templated)
    assert e["interpretation_source"] == "template"
    assert e["failure_mode"] in (None, *uam.mb.FAILURE_MODES)
