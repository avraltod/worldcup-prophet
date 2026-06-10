"""Reproducibility guard: every figure used in the paper MUST be produced by a
committed script in scripts/. Fails (exit 1) and lists any figure whose filename
does not appear in any scripts/*.py — i.e. an ad-hoc figure with no regenerator.
Run before compiling or committing:  python3 scripts/check_figures.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
tex = (ROOT / "paper" / "Avraa_WC2026_paper.tex").read_text()
used = sorted(set(re.findall(r"figs/([A-Za-z0-9_]+)\.(?:pdf|png)", tex)))
src = "\n".join(p.read_text(errors="ignore") for p in (ROOT / "scripts").glob("*.py")
                if p.name != "check_figures.py")

orphans = [f for f in used if f not in src]
for f in used:
    print(f"  {'OK     ' if f not in orphans else 'MISSING'}  {f}")

if orphans:
    print(f"\nFAIL: {len(orphans)} paper figure(s) have no generator script:")
    for f in orphans:
        print(f"   - {f}")
    print("Write a scripts/*.py that savefig()s each, then re-run.")
    sys.exit(1)

print(f"\nOK: all {len(used)} paper figures have a committed generator script.")
