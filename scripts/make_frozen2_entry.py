"""Persist the issued Frozen-2 knockout entry to data/frozen2_entry.json, the
immutable Stage-2 'expectations' the per-game knockout editions read. Generated
once from the pre-registered ko_repick optimizer on the realized R32 bracket."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ko_repick as kr
import ko_match_ev as kme

DATA = Path(__file__).resolve().parent.parent / "data"


def build():
    results = json.loads((DATA / "results_log_v2.json").read_text())
    eff = kme.load_live_eff()
    entry = kr.optimize_entry(results, eff=eff, N=20000, seed=2026)
    out = {"champion": entry["champion"], "picks": {}}
    for m, p in entry["picks"].items():
        ph, pa = kme.matchup_lambdas(p["home"], p["away"], eff)
        padv, _ = kme.advance_probs(ph, pa)
        out["picks"][str(m)] = {
            "home": p["home"], "away": p["away"], "advancer": p["advancer"],
            "score": list(p["score"]), "disp": list(p["disp"]), "pen": p["pen"],
            "ev": round(p["ev"], 4),
            "adv_prob": round(padv if p["advancer"] == p["home"] else 1 - padv, 4)}
    return out


if __name__ == "__main__":
    (DATA / "frozen2_entry.json").write_text(json.dumps(build(), ensure_ascii=False, indent=1))
    print("wrote data/frozen2_entry.json")
