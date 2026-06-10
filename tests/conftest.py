import sys
from pathlib import Path

# make scripts/ importable as top-level modules in tests
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
