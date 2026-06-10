from fetch_xg import fetch_real_xg

def test_returns_none_when_no_source_wired():
    # default: no free source implemented yet -> graceful None, no exception
    assert fetch_real_xg("633790", home="Qatar", away="Ecuador") is None

def test_never_raises_on_bad_input():
    # garbage in -> None, not an exception
    assert fetch_real_xg(None) is None
    assert fetch_real_xg("") is None
