"""Most-likely bracket builder: occupancy is the argmax of finishing-place
probability per group, 1st/2nd/3rd are distinct, and the structure matches the
submitted bracket geometry."""
import json
from pathlib import Path

import make_bracket_tikz as bt
import ml_bracket as mlb

DATA = Path(__file__).parent.parent / "data"
EXP = json.loads((DATA / "match_expectations.json").read_text())


def test_group_rosters_12x4_match_seed():
    rosters = mlb.group_rosters(EXP)
    assert sorted(rosters) == list("ABCDEFGHIJKL")
    assert all(len(v) == 4 for v in rosters.values())
    # every SEED team belongs to the group its identity names
    for team, ident in bt.SEED.items():
        assert team in rosters[ident[0]]


def test_place_occupants_distinct_and_argmax():
    rosters = mlb.group_rosters(EXP)
    # synthetic probs: in Group D make Australia the clear 2nd, Turkey low
    probs = {t: {"first": 0.0, "second": 0.0, "third_adv": 0.0} for g in rosters.values() for t in g}
    probs["United States"].update(first=0.9, second=0.05)
    probs["Australia"].update(first=0.05, second=0.6, third_adv=0.2)
    probs["Paraguay"].update(second=0.2, third_adv=0.5)
    probs["Turkey"].update(second=0.15, third_adv=0.25)
    occ = mlb.place_occupants(probs, rosters)
    # D1/D2/D3 present and distinct
    d = [occ[("D", p)][0] for p in (1, 2, 3)]
    assert len(set(d)) == 3
    assert occ[("D", 1)][0] == "United States"
    assert occ[("D", 2)][0] == "Australia"          # not Turkey -> reversal
    assert occ[("D", 2)][1] == 0.6                   # value = its 'second' prob
    # probabilities are in range
    assert all(0.0 <= v <= 1.0 for _, v in occ.values())


def test_build_shapes_and_champion():
    rosters = mlb.group_rosters(EXP)
    # uniform-ish probs so argmax is well-defined (alphabetical tie-break)
    probs = {t: {"first": 0.5, "second": 0.3, "third_adv": 0.1, "champion": 0.02}
             for g in rosters.values() for t in g}
    # deterministic winner by name so the test needs no ratings
    ml = mlb.build(probs, rosters, mlb.rating_winner(lambda t, late: hash(t) % 1000))
    for half in (ml["left"], ml["right"]):
        assert len(half["R32"]) == 8 and all(len(x) == 5 for x in half["R32"])
        assert len(half["R16"]) == 4
        assert len(half["QF"]) == 2
        assert isinstance(half["SF"], str)
    assert ml["champion"] in (ml["left"]["SF"], ml["right"]["SF"])
    # every R32 winner is one of that match's two entrants
    for half in (ml["left"], ml["right"]):
        for mlh, mla, w, _, _ in half["R32"]:
            assert w in (mlh, mla)
