from version import is_newer


def test_is_newer():
    assert is_newer("v1.2.0", "1.1.0")
    assert is_newer("v1.10", "1.9.9")
    assert not is_newer("v1.1.0", "1.1.0")
    assert not is_newer("v1.0", "1.1.0")
