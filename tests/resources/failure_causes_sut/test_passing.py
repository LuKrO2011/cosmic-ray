"""Dummy tests that always pass — used to verify SURVIVED outcome."""
from sut import add


def test_add_passes():
    assert add(1, 2) == 3
