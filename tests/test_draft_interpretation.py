import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import draft_interpretation as di

ENTRY = {"fixture": "Mexico v South Africa", "result": [2, 0],
         "pre": {"pick": [2, 1], "probs_HDA": [0.6718, 0.2087, 0.1193]},
         "post": {"points": 1, "brier": 0.1655, "p_outcome": 0.6718, "info_bits": 0.0011}}

def test_templated_is_deterministic_and_mentions_key_facts():
    a = di.templated(ENTRY)
    b = di.templated(ENTRY)
    assert a == b                       # deterministic
    assert "1 of 3" in a or "1/3" in a  # the points
    assert "0.001" in a                 # info_bits, low-movement story

def test_draft_falls_back_to_template_without_api():
    text, source = di.draft(ENTRY, corrections="", use_api=False)
    assert source == "template"
    assert text == di.templated(ENTRY)


def test_templated_revision_is_deterministic_and_grounded():
    import draft_interpretation as di
    pack = {"edition": 3, "fixture": "Canada v Bosnia and Herzegovina",
            "result": [2, 0], "points": 3, "info_bits": 0.02,
            "champ_deltas": [["Spain", 0.269, 0.280]],
            "lam_obs": {"home": 1.9, "away": 0.4},
            "lam_exp": {"home": 1.5, "away": 0.7}}
    a = di.templated_revision(pack)
    assert "Canada" in a and ("2--0" in a or "2-0" in a)
    assert a == di.templated_revision(pack)


def test_draft_revision_falls_back_without_key(monkeypatch):
    import draft_interpretation as di
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text, source = di.draft_revision({"edition": 1, "fixture": "A v B",
                                      "result": [1, 0], "points": 1,
                                      "info_bits": 0.0, "champ_deltas": [],
                                      "lam_obs": None, "lam_exp": None}, "", True)
    assert source == "template" and text
