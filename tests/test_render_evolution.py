import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import render_evolution as re_

SAMPLE = ("FROZEN ABOVE\n"
          "% LIVE-EVOLUTION-TABLE:START\n"
          "old table\n"
          "% LIVE-EVOLUTION-TABLE:END\n"
          "FROZEN BELOW\n")

ENTRIES = [
    {"match": 1, "fixture": "Mexico v South Africa", "result": [2, 0],
     "failure_mode": None,
     "pre": {"pick": [2, 1]},
     "post": {"points": 1, "brier": 0.1655, "info_bits": 0.0011},
     "interpretation": "A likely home win arrived; the title race barely moved."},
]

def test_replace_markers_only_touches_the_block():
    out = re_.replace_markers(SAMPLE, "LIVE-EVOLUTION-TABLE", "NEW\nROWS")
    assert "FROZEN ABOVE" in out and "FROZEN BELOW" in out
    assert "old table" not in out
    assert "NEW\nROWS" in out

def test_missing_marker_raises():
    try:
        re_.replace_markers("no markers here", "LIVE-EVOLUTION-TABLE", "x")
        assert False, "expected ValueError"
    except ValueError:
        pass

def test_frozen_hash_ignores_marker_contents():
    h1 = re_.frozen_hash(SAMPLE)
    changed = re_.replace_markers(SAMPLE, "LIVE-EVOLUTION-TABLE", "totally different")
    assert re_.frozen_hash(changed) == h1     # frozen text unchanged

def test_ledger_table_has_one_row_per_entry():
    tex = re_.ledger_table(ENTRIES)
    assert "Mexico v South Africa" in tex
    assert "2--0" in tex          # result rendered with en-dash
    assert tex.count(r"\\") >= 1  # at least one table row
