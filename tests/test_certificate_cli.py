import io
import json
import pytest
from types import SimpleNamespace

from lean_kernel_verifier.runner.checker_runner import CheckerRunResult


def test_cli_routes_pair_certificates_and_rejects_extra_fields(monkeypatch, capsys):
    from lean_kernel_verifier.__main__ import main
    calls = []
    def run(source):
        calls.append(source)
        return CheckerRunResult(True, 0, '', '', 1, False)
    monkeypatch.setattr('lean_kernel_verifier.__main__.LeanCheckerRunner', lambda _: SimpleNamespace(run_source=run, close=lambda: None))
    monkeypatch.setattr('sys.argv', ['verifier'])
    payload = {'specification': {'kind': 'count_pairs', 'expression': 'x < y', 'x_start': 0, 'x_stop': 2,
                                 'y_start': 0, 'y_stop': 2}, 'pairs': [[0, 1]], 'answer': 1}
    monkeypatch.setattr('sys.stdin', io.StringIO(json.dumps(payload)))
    assert main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result['scope'] == 'encoded_bounded_pair_count_with_complete_enumeration'
    assert len(result['certificate_digest']) == 64
    assert 'claimed_pairs = valid_pairs' in calls[0]
    payload['trusted'] = True
    monkeypatch.setattr('sys.stdin', io.StringIO(json.dumps(payload)))
    assert main() == 2 and len(calls) == 1


@pytest.mark.parametrize('payload', [
    '{"specification":{"kind":"evaluate","expression":"4"},"answer":4,"answer":5}',
    '{"specification":{"kind":"evaluate","expression":"4","expression":"5"},"answer":4}',
    '{"specification":{"kind":"evaluate","expression":"4"},"specification":{"kind":"evaluate","expression":"5"},"answer":4}',
    '{"specification":{"kind":"evaluate","expression":"4"},"answer":' + '[' * 2000 + '4' + ']' * 2000 + '}',
])
def test_cli_rejects_ambiguous_or_deep_json_before_native_execution(monkeypatch, capsys, payload):
    from lean_kernel_verifier.__main__ import main

    def run(source):
        pytest.fail('invalid request reached the checker')

    monkeypatch.setattr('lean_kernel_verifier.__main__.LeanCheckerRunner',
                        lambda _: SimpleNamespace(run_source=run, close=lambda: None))
    monkeypatch.setattr('sys.argv', ['verifier'])
    monkeypatch.setattr('sys.stdin', io.StringIO(payload))
    assert main() == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'invalid_input'
