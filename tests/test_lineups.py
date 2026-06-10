import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import lineups

ROOT = Path(__file__).resolve().parent.parent
SUMMARY = json.loads((ROOT / "data" / "espn_summary_sample.json").read_text())

def test_parse_lineup_extracts_eleven_starters_per_side():
    lu = lineups.parse_lineup(SUMMARY)
    assert lu is not None
    assert len(lu["home"]) == 11 and len(lu["away"]) == 11
    assert all(isinstance(n, str) and n for n in lu["home"] + lu["away"])

def test_parse_lineup_none_when_no_rosters():
    assert lineups.parse_lineup({}) is None
    assert lineups.parse_lineup({"rosters": []}) is None

def test_fetch_lineup_uses_injected_opener():
    class FakeResp:
        def __init__(self, text): self._t = text
        def read(self): return self._t.encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    captured = {}
    def opener(url, timeout=0):
        captured["url"] = url
        return FakeResp(json.dumps(SUMMARY))
    lu = lineups.fetch_lineup(633850, opener=opener)
    assert "event=633850" in captured["url"]
    assert len(lu["home"]) == 11
