"""Dummy tests that always fail with AssertionError — used to verify KILLED_ASSERTION."""
from sut import add


def test_add_wrong_result():
    assert add(1, 2) == 99  # always fails with AssertionError
