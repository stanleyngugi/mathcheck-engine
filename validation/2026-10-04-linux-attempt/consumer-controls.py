"""Observed installed-wheel controls; transport fixture is explicitly non-Lean."""
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

import lean_kernel_verifier
from lean_kernel_verifier.runner.checker_runner import CheckerRunConfig, LeanCheckerRunner
from lean_kernel_verifier.specification import ProblemSpec, verify_answer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = ROOT / 'mathcheck-engine'
TOOLCHAIN = ROOT / 'toolchains/lean-4.23.0-linux'
LEAN = TOOLCHAIN / 'bin/lean'
WHEEL = HERE / 'build-a/lean_kernel_verifier-0.3.3-py3-none-any.whl'
env = dict(os.environ)
env.pop('PYTHONPATH', None)
env['LD_LIBRARY_PATH'] = f'{TOOLCHAIN}/lib/lean:{TOOLCHAIN}/lib'

def execute(command, payload=None, environment=env):
    proc = subprocess.run(command, input=payload, text=True, capture_output=True,
                          cwd=HERE, env=environment, timeout=35)
    return {'command': command, 'returncode': proc.returncode,
            'stdout': proc.stdout, 'stderr': proc.stderr}

results = {
    'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip(),
    'python': sys.version,
    'platform': platform.platform(),
    'cwd': str(Path.cwd()),
    'installed_module': lean_kernel_verifier.__file__,
    'version': importlib.metadata.version('lean-kernel-verifier'),
    'installed_packages': sorted(f'{d.metadata["Name"]}=={d.version}' for d in importlib.metadata.distributions()),
    'toolchain_version_probe': execute([str(LEAN), '--version']),
    'bubblewrap_version': execute(['bwrap', '--version']),
    'bubblewrap_capability_probe': execute(['bwrap', '--ro-bind', '/', '/', '--', '/bin/true']),
    'proc_self_exe_available': Path('/proc/self/exe').exists(),
    'proc_overflowuid_available': Path('/proc/sys/kernel/overflowuid').exists(),
    'cli': [],
}
assert SOURCE not in Path(lean_kernel_verifier.__file__).parents
assert results['version'] == lean_kernel_verifier.__version__ == '0.3.3'
installed_root = Path(lean_kernel_verifier.__file__).parent.parent
with zipfile.ZipFile(WHEEL) as archive:
    entries = [name for name in archive.namelist() if name.startswith('lean_kernel_verifier/') and name.endswith('.py')]
    for name in entries:
        assert archive.read(name) == (SOURCE / name).read_bytes() == (installed_root / name).read_bytes(), name
results['source_wheel_installed_python_files_identical'] = len(entries)

controls = [
    ('duplicate_answer', '{"specification":{"kind":"evaluate","expression":"4"},"answer":4,"answer":5}', 'invalid_input'),
    ('duplicate_nested_expression', '{"specification":{"kind":"evaluate","expression":"4","expression":"5"},"answer":4}', 'invalid_input'),
    ('boolean_answer', {'specification': {'kind': 'evaluate', 'expression': '4'}, 'answer': True}, 'invalid_input'),
    ('malformed_pair', {'specification': {'kind': 'count_pairs', 'expression': 'x < y', 'x_start': 0, 'x_stop': 2, 'y_start': 0, 'y_stop': 2}, 'pairs': [[0]], 'answer': 1}, 'invalid_input'),
]
for kind, expression, start, stop, answer in [
    ('evaluate', '(7**5 - 3)//2 % 97', None, None, 60),
    ('count', 'x%3 == 0 and x%5 != 0', 1, 31, 8),
    ('sum', 'x*x-2*x', 2, 9, 133),
    ('minimum', 'x%7 == 3 and x%5 == 2', 0, 100, 17),
]:
    spec = {'kind': kind, 'expression': expression}
    if start is not None:
        spec.update(start=start, stop=stop)
    for candidate, expected in [(answer, 'checked_success'), (answer+1, 'mathematical_rejection')]:
        controls.append((f'{kind}_{candidate}', {'specification': spec, 'answer': candidate}, expected))
controls.append(('minimum_feasible_nonminimal_52', {'specification': {'kind': 'minimum', 'expression': 'x%7 == 3 and x%5 == 2', 'start': 0, 'stop': 100}, 'answer': 52}, 'mathematical_rejection'))
pair_spec = {'kind': 'count_pairs', 'expression': 'x < y and x+y == 4', 'x_start': 0, 'x_stop': 5, 'y_start': 0, 'y_stop': 5}
controls.extend([
    ('pairs_complete', {'specification': pair_spec, 'pairs': [[0, 4], [1, 3]], 'answer': 2}, 'checked_success'),
    ('pairs_incomplete', {'specification': pair_spec, 'pairs': [[0, 4]], 'answer': 1}, 'mathematical_rejection'),
    ('pairs_wrong_cardinality', {'specification': pair_spec, 'pairs': [[0, 4], [1, 3]], 'answer': 1}, 'mathematical_rejection'),
])
for label, payload, expected in controls:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    result = execute([sys.executable, '-m', 'lean_kernel_verifier', '--lean-bin', str(LEAN)], raw)
    parsed = json.loads(result['stdout'])
    result.update(label=label, request=payload, expected_on_capable_host=expected, parsed=parsed)
    if expected == 'invalid_input':
        assert result['returncode'] == 2 and parsed['status'] == expected
    else:
        # On this host the stock executable fails its version preflight. This is
        # an operational control, never a native mathematical pass or rejection.
        assert result['returncode'] == 1 and parsed['status'] == 'operational_error'
        assert not parsed['verified'] and parsed['checker']['backend_error']
        assert not parsed['checker']['timed_out']
    results['cli'].append(result)

for label, executable in [('stock_lean_exact_version', str(LEAN)), ('missing_executable', str(HERE / 'does-not-exist'))]:
    runner = LeanCheckerRunner(CheckerRunConfig(lean_executable=executable, required_lean_version=(4, 23, 0)))
    try:
        verdict = verify_answer(ProblemSpec('evaluate', '2+2'), 4, runner)
        assert not verdict.verified and verdict.status == 'operational_error' and verdict.checker.backend_error
        results[label] = asdict(verdict)
    finally:
        runner.close()

# A real subprocess timeout with a deliberately non-Lean transport fixture.
# It prints a version-shaped string solely to exercise the existing preflight.
fixture = HERE / 'non_lean_timeout_fixture.py'
fixture.write_text(f'#!{sys.executable}\nimport sys, time\nif "--version" in sys.argv:\n    print("NON-LEAN TEST FIXTURE version 4.23.0")\nelse:\n    time.sleep(5)\n')
fixture.chmod(0o700)
runner = LeanCheckerRunner(CheckerRunConfig(lean_executable=str(fixture), timeout_seconds=1))
try:
    verdict = verify_answer(ProblemSpec('evaluate', '2+2'), 4, runner)
    assert not verdict.verified and verdict.status == 'operational_error' and verdict.checker.timed_out
    results['non_lean_subprocess_timeout_fixture'] = asdict(verdict)
finally:
    runner.close()

unconfigured = dict(env)
unconfigured.pop('LKV_SANDBOX_TOOLCHAIN', None)
results['isolated_unconfigured'] = execute([str(Path(sys.executable).parent / 'lean-isolated'), '--version'], environment=unconfigured)
configured = dict(env, LKV_SANDBOX_TOOLCHAIN=str(TOOLCHAIN))
results['isolated_configured'] = execute([str(Path(sys.executable).parent / 'lean-isolated'), '--version'], environment=configured)
assert results['isolated_unconfigured']['returncode'] == 125
assert results['isolated_configured']['returncode'] == 125
(HERE / 'consumer-controls.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps({'controls': len(results['cli']), 'python_file_identity': len(entries),
                  'lean_startup_exit': results['toolchain_version_probe']['returncode'],
                  'bwrap_probe_exit': results['bubblewrap_capability_probe']['returncode'],
                  'native_mathematical_passes': 0, 'native_mathematical_rejections': 0,
                  'timeout_transport_fixture_passed': True}, indent=2))
