"""Opt-in Linux CLI isolation. Missing namespaces/tools are fatal, never bypassed.

This restricts filesystem/network access and individual process resources. It is
not a substitute for a separately audited multi-tenant service or aggregate cgroups.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile


def isolated_command(toolchain: Path, work: Path, arguments: list[str]) -> list[str]:
    toolchain, work = toolchain.resolve(strict=True), work.resolve(strict=True)
    if not (toolchain / 'bin' / 'lean').is_file() or toolchain == Path('/'):
        raise ValueError('supply the standalone pinned Lean distribution root')
    bwrap, prlimit = shutil.which('bwrap'), shutil.which('prlimit')
    if not bwrap or not prlimit or sys.platform != 'linux':
        raise RuntimeError('Linux bubblewrap and prlimit are required; no unisolated fallback')
    command = [prlimit, '--as=2147483648', '--cpu=120', '--fsize=16777216', '--nofile=128', '--core=0', '--',
               bwrap, '--unshare-all', '--die-with-parent', '--new-session', '--cap-drop', 'ALL',
               '--clearenv', '--setenv', 'PATH', '/opt/lean/bin:/usr/bin', '--setenv', 'HOME', '/tmp',
               '--ro-bind', '/usr', '/usr']
    for path in ('/lib', '/lib64', '/bin'):
        if Path(path).exists():
            command += ['--ro-bind', str(Path(path).resolve()), path]
    command += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
                '--dir', '/opt', '--ro-bind', str(toolchain), '/opt/lean',
                '--bind', str(work), '/work', '--chdir', '/work', '/opt/lean/bin/lean', *arguments]
    return command


def toolchain_identity(toolchain: Path) -> dict:
    """Binary fingerprint for audit records, not a supply-chain attestation."""
    lean = toolchain.resolve(strict=True) / 'bin' / 'lean'
    digest = hashlib.sha256()
    with lean.open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''):
            digest.update(block)
    return {'lean_binary_sha256': digest.hexdigest(), 'required_version': '4.23.0',
            'scope': 'Lean executable only; not a hash of the compiler, libraries, or OS'}


def main():
    args = sys.argv[1:]
    if len(args) != 1 or (args[0].startswith('-') and args[0] != '--version'):
        print('lean-isolated accepts --version or a single Lean source file; CLI backend only', file=sys.stderr)
        return 125
    root = os.environ.get('LKV_SANDBOX_TOOLCHAIN')
    if not root:
        print('LKV_SANDBOX_TOOLCHAIN is required; no unisolated fallback', file=sys.stderr)
        return 125
    try:
        with tempfile.TemporaryDirectory(prefix='lkv_isolated_') as temporary:
            directory = Path(temporary)
            work = directory / 'work'
            work.mkdir()
            arguments = ['--version']
            if args[0] != '--version':
                with Path(args[0]).open('rb') as source:
                    data = source.read(2_000_001)
                if len(data) > 2_000_000:
                    raise ValueError('source exceeds 2 MB limit')
                (work / 'input.lean').write_bytes(data)
                arguments = ['/work/input.lean']
            command = isolated_command(Path(root), work, arguments)
            if args[0] != '--version':
                version = subprocess.run(isolated_command(Path(root), work, ['--version']),
                                         capture_output=True, text=True, timeout=30,
                                         env={'PATH': '/usr/bin:/bin'})
                if version.returncode != 0 or 'Lean (version 4.23.0,' not in version.stdout:
                    print('isolated checker requires an accessible Lean 4.23.0 toolchain', file=sys.stderr)
                    return 125
            with (directory / 'output.log').open('w+b') as output:
                proc = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                        start_new_session=True, env={'PATH': '/usr/bin:/bin'})
                try:
                    returncode = proc.wait(timeout=150)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                    print('isolated Lean exceeded wall-clock limit', file=sys.stderr)
                    return 124
                output.seek(0)
                data = output.read(262145)
                if len(data) > 262144:
                    print('isolated Lean exceeded diagnostic output limit', file=sys.stderr)
                    return 125
                text = data.decode(errors='replace')
                print(text, end='')
                if args[0] == '--version' and 'Lean (version 4.23.0,' not in text:
                    print('isolated checker requires Lean 4.23.0', file=sys.stderr)
                    return 125
                return returncode if returncode >= 0 else 125
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'isolation failed: {exc}', file=sys.stderr)
        return 125


if __name__ == '__main__':
    raise SystemExit(main())
