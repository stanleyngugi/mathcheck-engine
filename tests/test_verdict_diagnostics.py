"""A failed compiler invocation must not become false mathematical evidence."""
import pytest

from lean_kernel_verifier.runner.checker_runner import CheckerRunResult
from lean_kernel_verifier.specification import checker_status


FALSE_MESSAGE = (
    'Tactic `native_decide` evaluated that the proposition\n'
    '  (Array.range expected.size).all (fun n => f n == expected[n]!) = true\n'
    'is false'
)


@pytest.mark.parametrize('prefix', ['verify.lean:43:2: error: ', '[43:2] ', 'error: '])
@pytest.mark.parametrize('stream', ['stdout', 'stderr'])
def test_complete_negative_decision_in_cli_or_lsp_output(prefix, stream):
    streams = {'stdout': '', 'stderr': ''}
    streams[stream] = prefix + FALSE_MESSAGE + '\n'
    result = CheckerRunResult(False, 1, **streams, duration_ms=1, timed_out=False)
    assert checker_status(result) == 'mathematical_rejection'


@pytest.mark.parametrize('output', [
    '', 'false', 'is false',
    'verify.lean:43:2: error: unsolved goals',
    'error: failed to locate application',
    'verify.lean:43:2: error: Tactic `native_decide` failed: Could not evaluate decidable instance',
    'verify.lean:43:2: error: ' + FALSE_MESSAGE.removesuffix('is false'),
    'verify.lean:43:2: error: ' + FALSE_MESSAGE + '\nverify.lean:44:2: error: unknown identifier',
    'warning: is false\nverify.lean:43:2: error: ' + FALSE_MESSAGE,
])
def test_unconfirmed_or_mixed_failure_is_operational(output):
    result = CheckerRunResult(False, 1, output, '', 1, False)
    assert checker_status(result) == 'operational_error'


def test_native_false_message_cannot_override_a_process_failure():
    for code in (124, 125, -9, 2):
        result = CheckerRunResult(False, code, 'error: ' + FALSE_MESSAGE, '', 1, False)
        assert checker_status(result) == 'operational_error'


def test_multiple_complete_negative_diagnostics_are_recognized():
    output = '\n'.join('verify.lean:43:2: error: ' + FALSE_MESSAGE for _ in range(2))
    assert checker_status(CheckerRunResult(False, 1, output, '', 1, False)) == 'mathematical_rejection'
