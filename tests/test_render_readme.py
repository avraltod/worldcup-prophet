import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import render_readme as rr

TRAJ = [{
    "label": "2026-06-12", "n_played": 3, "info_bits": 0.0123,
    "champion": {"Spain": 0.262, "Argentina": 0.181, "France": 0.121},
    "market_champion": {"Spain": 0.155, "Argentina": 0.142, "France": 0.110},
    "top_movers": [["Mexico", 1.4], ["South Africa", -1.1]],
}]
LOG = {"group": {"4": [2, 1]}, "ko": {}}

def test_render_block_contains_key_facts():
    block = rr.render_results_block(TRAJ, LOG)
    assert "3/104" in block
    assert "0.012 bits" in block
    assert "Spain" in block and "26.2%" in block and "15.5%" in block
    assert "M4:" in block and "Mexico" in block and "2" in block

def test_replace_block_only_between_markers():
    text = ("intro\n<!-- LIVE-RESULTS:START -->\nOLD\n<!-- LIVE-RESULTS:END -->\noutro\n")
    out = rr.replace_readme_block(text, "NEW")
    assert "OLD" not in out and "NEW" in out
    assert out.startswith("intro\n") and out.rstrip().endswith("outro")

def test_replace_block_raises_if_markers_missing():
    import pytest
    with pytest.raises(ValueError):
        rr.replace_readme_block("no markers here", "NEW")
