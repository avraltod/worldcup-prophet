import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

def test_frozen2_entry_is_complete_and_typed():
    d = json.loads((ROOT / "data" / "frozen2_entry.json").read_text())
    assert d["champion"]
    picks = d["picks"]
    assert {int(m) for m in picks} == set(range(73, 105))  # 73..104, all 32 KO slots
    for m, p in picks.items():
        assert p["home"] and p["away"] and p["advancer"] in (p["home"], p["away"])
        assert len(p["disp"]) == 2 and isinstance(p["pen"], bool)
        assert 0.0 <= p["adv_prob"] <= 1.0 and isinstance(p["ev"], float)
