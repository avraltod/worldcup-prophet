"""Guards the official match-number mapping used to key results_log["group"].
The live pipeline keys group results by OFFICIAL FIFA match number (1-72) via
fixtures.ROW_MATCH; condition.py / record_update.py read them under the same
numbers. fixtures.ROW_MATCH is a copy of condition.ROW_MATCH — this test fails
if the two ever drift, and pins the opener as match 1 (the bug this prevents:
keying by sheet row 4-75 instead, which silently mis-conditions the forecast)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_results as fr
from fixtures import ROW_MATCH
import condition


def test_fixtures_row_match_equals_condition():
    assert ROW_MATCH == condition.ROW_MATCH


def test_row_match_covers_1_to_72():
    assert set(ROW_MATCH.values()) == set(range(1, 73))


def test_opener_maps_to_official_match_1():
    # Mexico v South Africa (sheet row 4) is official match number 1
    assert fr.map_to_fixture("Mexico", "South Africa")[0] == 1
    # USA v Paraguay (sheet row 22) is official match number 4
    assert fr.map_to_fixture("United States", "Paraguay")[0] == 4
    # Brazil v Haiti (sheet row 19) is official match number 29
    assert fr.map_to_fixture("Brazil", "Haiti")[0] == 29
