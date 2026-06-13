"""Tests for pipeline figure generation scripts.

Source tests (no graphviz binary needed): verify DOT source contains required
nodes, colors, and labels. Integration tests (mark integration): verify the
rendered PDF exists and is non-trivial.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT  = Path(__file__).parent.parent
FIGS  = ROOT / "paper" / "figs"
sys.path.insert(0, str(ROOT / "scripts"))


# ── Source-level tests (no binary) ──────────────────────────────────────────

def test_overview_source_has_required_nodes():
    import fig_pipeline_overview as m
    src = m.build().source
    assert "ESPN scoreboard API" in src
    assert "ESPN box score API"  in src
    assert "Part I" in src
    assert "Part II" in src
    assert "Champion probabilities" in src
    assert "104 match predictions" in src
    assert "Match is" in src          # the diamond event node


def test_overview_source_has_live_cluster():
    import fig_pipeline_overview as m
    src = m.build().source
    assert "Repeats after each of 104 matches" in src


def test_part1_source_has_two_input_lanes():
    import fig_pipeline_part1 as m
    src = m.build().source
    assert "Bookmaker odds JSON" in src
    assert "Elo synthesis"       in src


def test_part1_source_has_full_pipeline():
    import fig_pipeline_part1 as m
    src = m.build().source
    assert "Poisson inversion" in src
    assert "Monte Carlo"       in src
    assert "Slot emergence"    in src
    assert "ML risk"           in src
    assert "EV-optimal pick"   in src
    assert "baseline\nfor Part II" in src   # dashed handoff arrow label


def test_part2_source_has_ingestion():
    import fig_pipeline_part2 as m
    src = m.build().source
    assert "ESPN scoreboard API" in src
    assert "Parse scoreboard"    in src
    assert "Parse box score"     in src


def test_part2_source_has_performance_signal():
    import fig_pipeline_part2 as m
    src = m.build().source
    assert "Proxy xG"     in src
    assert "Net surprise" in src
    assert "0.3256"       in src


def test_part2_source_has_two_tracks():
    import fig_pipeline_part2 as m
    src = m.build().source
    assert "Track A" in src
    assert "Track B" in src
    assert "Drift update" in src
    assert "KL divergence" in src


def test_part2_source_has_feedback_arrow():
    import fig_pipeline_part2 as m
    src = m.build().source
    assert "next match" in src   # cross-match dashed feedback label


def test_node_colors_consistent_across_figures():
    """Data=blue, transform=orange, output=green in every figure."""
    import fig_pipeline_overview as ov
    import fig_pipeline_part1    as p1
    import fig_pipeline_part2    as p2
    for mod in (ov, p1, p2):
        src = mod.build().source
        assert "#4472C4" in src, f"blue missing in {mod.__name__}"
        assert "#ED7D31" in src, f"orange missing in {mod.__name__}"
        assert "#70AD47" in src, f"green missing in {mod.__name__}"


# ── Integration tests (need graphviz binary) ────────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("script,pdf", [
    ("fig_pipeline_overview.py", "fig_pipeline_overview.pdf"),
    ("fig_pipeline_part1.py",    "fig_pipeline_part1.pdf"),
    ("fig_pipeline_part2.py",    "fig_pipeline_part2.pdf"),
])
def test_script_produces_pdf(script, pdf):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"{script} exited non-zero:\n{result.stderr}"
    out = FIGS / pdf
    assert out.exists(),              f"{pdf} not found after running {script}"
    assert out.stat().st_size > 2000, f"{pdf} suspiciously small (< 2 KB)"
