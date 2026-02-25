"Support for running tests in a subprocess."

import logging
import os
import re
import shlex
import subprocess
import traceback

from cosmic_ray.work_item import TestOutcome

log = logging.getLogger(__name__)

_ASSERTION_TYPES = frozenset({"AssertionError", "Failed"})


def _classify_failure(output: str) -> TestOutcome:
    """Parse pytest output to classify how a test killed the mutant.

    Returns KILLED_ASSERTION if all failures raised AssertionError or pytest's
    own "Failed:" (e.g. if a expected exception was not raised).
	Returns KILLED_EXCEPTION if any failure used a different exception.
	Returns KILLED when the output cannot be parsed.
    """
    # Primary: summary lines that carry the exception type explicitly.
    # Format: "FAILED path::test - ExcType: message"
    summary = re.findall(r"^FAILED .+ - (.+?)(?::|$)", output, re.MULTILINE)
    if summary:
        types = [t.strip() for t in summary]
        return TestOutcome.KILLED_EXCEPTION if any(t not in _ASSERTION_TYPES for t in types) else TestOutcome.KILLED_ASSERTION

    # Fallback: collect exception types from:
    #   • "E   ExcType:" prefixed traceback lines
    #   • "path:line: ExcType" footer lines (pytest assertion rewriting emits no
    #     exception-type prefix on "E   assert ..." lines, only the footer)
    exc_types = re.findall(
        r"(?:^E\s+|^\S+:\d+: )(\w[\w.]*(?:Error|Exception)|Failed)(?::|$)",
        output, re.MULTILINE,
    )
    if exc_types:
        return TestOutcome.KILLED_EXCEPTION if any(t not in _ASSERTION_TYPES for t in exc_types) else TestOutcome.KILLED_ASSERTION

    # FAILED lines present but no typed exception captured due to assertion rewriting
    # only applies to AssertionError, so treat as assertion kill.
    if re.search(r"^FAILED ", output, re.MULTILINE):
        return TestOutcome.KILLED_ASSERTION

    return TestOutcome.KILLED


# We use an asyncio-subprocess-based approach here instead of a simple
# subprocess.run()-based approach because there are problems with timeouts and
# reading from stderr in subprocess.run. Since we have to be prepared for test
# processes that run longer than timeout (and, indeed, which run forever), the
# broken subprocess stuff simply doesn't work. So we do this, which seems to
# work on all platforms.


def run_tests(command, timeout):
    """Run test command in a subprocess.

    If the command exits with status 0, then we assume that all tests passed. If
    it exits with any other code, we assume a test failed. If the call to launch
    the subprocess throws an exception, we consider the test 'incompetent'.

    Tests which time out are considered 'killed' as well.

    Args:
        command (str): The command to execute.
        timeout (number): The maximum number of seconds to allow the tests to run.

    Return: A tuple `(TestOutcome, output)` where the `output` is a string
        containing the output of the command.
    """
    log.info("Running test (timeout=%s): %s", timeout, command)

    # We want to avoid writing pyc files in case our changes happen too fast for Python to
    # notice them. If the timestamps between two changes are too small, Python won't recompile
    # the source.
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    try:
        proc = subprocess.run(shlex.split(command), check=True, env=env, timeout=timeout, capture_output=True)
        assert proc.returncode == 0
        return (TestOutcome.SURVIVED, proc.stdout.decode("utf-8"))

    except subprocess.CalledProcessError as err:
        output = err.output.decode("utf-8")
        return (_classify_failure(output), output)

    except subprocess.TimeoutExpired:
        return (TestOutcome.KILLED, "timeout")

    except Exception:  # pylint: disable=W0703
        return (TestOutcome.INCOMPETENT, traceback.format_exc())
