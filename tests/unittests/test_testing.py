"""Tests for cosmic_ray.testing module."""

from pathlib import Path

import cosmic_ray.work_item as work_item
from cosmic_ray.testing import _classify_failure, run_tests

DUMMY_SUT_DIR = Path(__file__).parent.parent.parent / "tests" / "resources" / "failure_causes_sut"


SUMMARY_ASSERTION_OUTPUT = """\
=========================== short test summary info ============================
FAILED tests/foo.py::test_bar - AssertionError: assert 1 == 2
FAILED tests/foo.py::test_baz - AssertionError: expected True
============================== 2 failed in 0.12s ==============================
"""

SUMMARY_EXCEPTION_OUTPUT = """\
=========================== short test summary info ============================
FAILED tests/foo.py::test_bar - TypeError: unsupported operand type(s)
============================== 1 failed in 0.05s ==============================
"""

SUMMARY_MIXED_OUTPUT = """\
=========================== short test summary info ============================
FAILED tests/foo.py::test_bar - AssertionError: assert 1 == 2
FAILED tests/foo.py::test_baz - TypeError: unsupported operand type(s)
============================== 2 failed in 0.08s ==============================
"""

SUMMARY_DID_NOT_RAISE_OUTPUT = """\
=========================== short test summary info ============================
FAILED tests/foo.py::test_raises - Failed: DID NOT RAISE <class 'SyntaxError'>
============================== 1 failed in 0.06s ==============================
"""

TRACEBACK_ASSERTION_OUTPUT = """\
    def test_something():
>       assert foo() == 42
E       AssertionError: assert 0 == 42
"""

TRACEBACK_EXCEPTION_OUTPUT = """\
    def test_something():
>       result = foo()
E       TypeError: unsupported operand type(s) for +: 'int' and 'str'
"""

TRACEBACK_MIXED_OUTPUT = """\
    def test_one():
>       assert foo() == 42
E       AssertionError: assert 0 == 42

    def test_two():
>       result = foo()
E       ValueError: invalid literal
"""

# Pytest assertion rewriting: no "E   AssertionError:" line, only location footer
LOCATION_ASSERTION_OUTPUT = """\
FAILED tests/foo.py::test_bar

    def test_bar():
>       assert add(1, 2) == 99
E       assert 3 == 99

tests/foo.py:6: AssertionError
============================== 1 failed in 0.19s ==============================
"""

LOCATION_EXCEPTION_OUTPUT = """\
FAILED tests/foo.py::test_bar

    def test_bar():
>       _ = "x" + 1
E       TypeError: ...

tests/foo.py:6: TypeError
============================== 1 failed in 0.05s ==============================
"""

COLLECTION_ERROR_OUTPUT = """\
collected 0 items / 1 error

==================================== ERRORS ====================================
___ ERROR collecting tests/test_sut.py ___
E   SyntaxError: invalid syntax (sut.py, line 5)

============================== 1 error in 0.12s ==============================
"""

EMPTY_OUTPUT = ""
UNRELATED_OUTPUT = "some random output with no pytest info"


class TestClassifyFailure:
    def test_summary_assertion_only(self):
        assert _classify_failure(SUMMARY_ASSERTION_OUTPUT) == work_item.TestOutcome.KILLED_ASSERTION

    def test_summary_exception(self):
        assert _classify_failure(SUMMARY_EXCEPTION_OUTPUT) == work_item.TestOutcome.KILLED_EXCEPTION

    def test_summary_mixed_any_exception_wins(self):
        assert _classify_failure(SUMMARY_MIXED_OUTPUT) == work_item.TestOutcome.KILLED_EXCEPTION

    def test_summary_did_not_raise_is_assertion(self):
        assert _classify_failure(SUMMARY_DID_NOT_RAISE_OUTPUT) == work_item.TestOutcome.KILLED_ASSERTION

    def test_traceback_assertion_fallback(self):
        assert _classify_failure(TRACEBACK_ASSERTION_OUTPUT) == work_item.TestOutcome.KILLED_ASSERTION

    def test_traceback_exception_fallback(self):
        assert _classify_failure(TRACEBACK_EXCEPTION_OUTPUT) == work_item.TestOutcome.KILLED_EXCEPTION

    def test_traceback_mixed_any_exception_wins(self):
        assert _classify_failure(TRACEBACK_MIXED_OUTPUT) == work_item.TestOutcome.KILLED_EXCEPTION

    def test_location_line_assertion(self):
        # pytest assertion rewriting: no "E   AssertionError:" line
        assert _classify_failure(LOCATION_ASSERTION_OUTPUT) == work_item.TestOutcome.KILLED_ASSERTION

    def test_location_line_exception(self):
        assert _classify_failure(LOCATION_EXCEPTION_OUTPUT) == work_item.TestOutcome.KILLED_EXCEPTION

    def test_collection_error_returns_killed_import(self):
        assert _classify_failure(COLLECTION_ERROR_OUTPUT) == work_item.TestOutcome.KILLED_IMPORT

    def test_error_collecting_line_returns_killed_import(self):
        output = "ERROR collecting tests/test_foo.py\nE   SyntaxError: invalid syntax\n"
        assert _classify_failure(output) == work_item.TestOutcome.KILLED_IMPORT

    def test_empty_output_returns_killed(self):
        assert _classify_failure(EMPTY_OUTPUT) == work_item.TestOutcome.KILLED

    def test_unrelated_output_returns_killed(self):
        assert _classify_failure(UNRELATED_OUTPUT) == work_item.TestOutcome.KILLED


class TestRunTestsIntegration:
    """Integration tests that call run_tests() against real dummy test files."""

    def _cmd(self, filename):
        return f"pytest {DUMMY_SUT_DIR / filename} -p no:cacheprovider"

    def test_survived_when_tests_pass(self):
        outcome, output = run_tests(self._cmd("test_passing.py"), timeout=30)
        assert outcome == work_item.TestOutcome.SURVIVED

    def test_killed_assertion_on_assert_failure(self):
        outcome, output = run_tests(self._cmd("test_assert_fail.py"), timeout=30)
        assert outcome == work_item.TestOutcome.KILLED_ASSERTION

    def test_killed_assertion_on_did_not_raise(self):
        outcome, output = run_tests(self._cmd("test_did_not_raise.py"), timeout=30)
        assert outcome == work_item.TestOutcome.KILLED_ASSERTION

    def test_killed_exception_on_type_error(self):
        outcome, output = run_tests(self._cmd("test_exception_fail.py"), timeout=30)
        assert outcome == work_item.TestOutcome.KILLED_EXCEPTION

    def test_killed_import_on_syntax_error(self):
        outcome, output = run_tests(self._cmd("test_import_error.py"), timeout=30)
        assert outcome == work_item.TestOutcome.KILLED_IMPORT
