import io
import json
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
