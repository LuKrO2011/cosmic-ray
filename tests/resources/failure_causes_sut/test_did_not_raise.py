"""Dummy test using pytest.raises that never sees the exception — KILLED_ASSERTION."""
import pytest
from sut import add


def test_expected_exception_never_raised():
    with pytest.raises(ValueError):
        add(1, 2)  # does not raise — pytest reports "Failed: DID NOT RAISE"
