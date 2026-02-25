"""Dummy tests that always fail with a non-assertion exception — KILLED_EXCEPTION."""


def test_type_error():
    _ = "string" + 1  # always raises TypeError
