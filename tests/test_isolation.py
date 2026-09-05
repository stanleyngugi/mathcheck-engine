import os
from pathlib import Path
import subprocess
import sys

import pytest

from lean_kernel_verifier.isolation import isolated_command, toolchain_identity


def test_missing_sandbox_is_fail_closed(monkeypatch, tmp_path):
    (tmp_path / 'bin').mkdir()
    (tmp_path / 'bin/lean').touch()
    monkeypatch.setattr('shutil.which', lambda _: None)
    with pytest.raises(RuntimeError):
        isolated_command(tmp_path, tmp_path, ['--version'])


def test_cli_does_not_fall_back_without_configuration(monkeypatch):
    from lean_kernel_verifier.isolation import main
    monkeypatch.delenv('LKV_SANDBOX_TOOLCHAIN', raising=False)
    monkeypatch.setattr(sys, 'argv', ['lean-isolated', '--version'])
    assert main() == 125


@pytest.mark.skipif(not os.environ.get('LEAN_BIN'), reason='set LEAN_BIN for live isolation')
def test_live_isolation_hides_host_files_and_environment(tmp_path):
    # An intentionally unsanitized Lean IO probe tests isolation, not theorem validity.
    toolchain = Path(os.environ['LEAN_BIN']).resolve().parent.parent
    marker = tmp_path / 'host-secret'
    marker.write_text('private')
    source = tmp_path / 'probe.lean'
    source.write_text('#eval show IO Unit from do\n'
                      f'  let visible ← System.FilePath.pathExists "{marker}"\n'
                      '  let secret ← IO.getEnv "LKV_TEST_SECRET"\n'
                      '  if visible || secret.isSome then throw (IO.userError "isolation failed")\n'
                      '  IO.println "isolation-ok"\n')
    env = dict(os.environ, LKV_SANDBOX_TOOLCHAIN=str(toolchain), LKV_TEST_SECRET='must-not-cross')
    proc = subprocess.run([sys.executable, '-m', 'lean_kernel_verifier.isolation', str(source)],
                          env=env, capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert 'isolation-ok' in proc.stdout
    assert len(toolchain_identity(toolchain)['lean_binary_sha256']) == 64


@pytest.mark.skipif(not os.environ.get('LEAN_BIN'), reason='set LEAN_BIN for live namespace probe')
def test_live_network_namespace_is_separate(tmp_path):
    toolchain = Path(os.environ['LEAN_BIN']).resolve().parent.parent
    command = isolated_command(toolchain, tmp_path, [])
    command[-1:] = ['/usr/bin/python3', '-c', 'import os; print(os.readlink("/proc/self/ns/net"))']
    proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() != os.readlink('/proc/self/ns/net')
