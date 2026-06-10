import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_results as fr
from fixtures import GROUP_FIXTURES

SNAP = json.loads((Path(__file__).resolve().parent.parent
                   / "data" / "espn_group_snapshot.json").read_text())

def test_all_72_group_fixtures_resolvable_from_espn():
    seen = set()
    unmapped = []
    for payload in SNAP.values():
        for m in fr.parse_scoreboard(payload):
            fx = fr.map_to_fixture(m["home"], m["away"])
            if fx is None:
                unmapped.append((m["home"], m["away"]))
            else:
                seen.add(fx[0])
    assert not unmapped, f"ESPN names not mapping to a fixture: {sorted(set(unmapped))}"
    expected_rows = {r for r, g, h, a in GROUP_FIXTURES}
    assert seen == expected_rows, f"missing rows: {sorted(expected_rows - seen)}"
