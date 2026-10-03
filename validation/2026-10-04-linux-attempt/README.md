# Engine 0.3.3: fresh Linux validation attempt

Recorded on 2026-10-04. **Release gate blocked; this is not native certification.**
The exact source tested and built was
`dce2fc88cee1e98ed3136ac89a4b40eba0d1ada7`. GitHub `main` matched that commit
before this evidence-only update. No implementation, mathematics, package metadata,
blog, or RL changes were made. No `AGENTS.md` was present in the checkout.

## What executed

| Check | Observed result |
| --- | --- |
| Source suite without `LEAN_BIN` | Exit 0: 85 passed, 10 required live skips, 40 subtests passed |
| Complete suite with the installed stock Lean binary explicitly configured | Exit 1: 19 failed, 87 passed, 41 subtests passed; no skips |
| Two wheel builds | Both succeeded; wheel bytes and SHA-256 identical |
| Supplementary source archives | Both built; regular file contents identical, archive bytes differ |
| Fresh wheel installation outside checkout | Succeeded; `pip check` passed |
| Installed package identity | Version 0.3.3; all 23 Python source files match wheel and audited source |
| Installed JSON CLI input controls | Duplicate top-level/nested keys, boolean answer, malformed pair: exit 2, `invalid_input` |
| Installed CLI mathematical controls | All 12 attempted controls returned exit 1, `operational_error`, `backend_error=true`; none compiled successfully |
| Installed API | Missing executable and exact-version stock Lean configuration fail operationally |
| Actual subprocess timeout | Passed using an explicitly non-Lean sleep fixture; not native Lean evidence |
| Installed isolation launcher | Unconfigured and configured calls exit 125; no fallback |

The live-suite summary contains failed unittest subtests as well as failed test
functions. Two parent test functions are included in its pass count despite their
failed subtests. All ten formerly skipped native/isolation test entries were
attempted; none of those ten required entries cleared its complete gate. Some
negative controls observe `verified=false` under infrastructure failure; that
alone does not establish mathematical rejection.

Source tests cover the complete recognized false-`native_decide` diagnostic,
unknown/mixed/truncated diagnostics, wrapper failures, signals, and timeout
classification. These are fixture-level classification results. This host
produced **zero current native mathematical acceptances and zero current native
mathematical rejections**.

## Installed toolchain and host

Python is 3.12.14; build/test dependencies are recorded in
`host-and-test-results.json`, and fresh consumer dependencies in
`consumer-controls.json`. The build tools were build 1.3.0, setuptools 80.9.0,
wheel 0.45.1, packaging 25.0, and pip 25.0.1. Tests used pytest 8.4.2,
pytest-subtests 0.15.0, and SymPy 1.14.0.

The official [Lean 4.23.0 Linux archive](https://github.com/leanprover/lean4/releases/download/v4.23.0/lean-4.23.0-linux.tar.zst)
was downloaded, extracted in this workspace, and made read-only. Its measured
size is 436,396,005 bytes. The archive SHA-256 matches the official release
asset digest:

```
ecd028d6f642b61b451c8687aeeb24dd53789fbfdcb7d4adb8f5cf60eb2022ba
```

The installed `bin/lean` SHA-256 is:

```
cbf5fd536e142ef1beaccf33f788fd8a7f3f29fb214e75c11319a8d8677b4b2b
```

Archive provenance and measured binary fingerprints are separate records in
`lean-provenance.json` and `toolchain.json`. **Lean's runtime version probe
does not succeed**: the stock binary exits 1 with
`error: failed to locate application`. This worker cannot certify its reported
runtime version merely from the release filename.

The machine runs Linux x86_64 and has bubblewrap 0.9.0, `prlimit`, and `unshare`.
It has no `/proc` directory. The bubblewrap capability probe exits 1:

```
bwrap: Can't read /proc/sys/kernel/overflowuid: No such file or directory
```

A separate user/mount namespace attempt exits 1:

```
unshare: cannot open /proc/self/uid_map: No such file or directory
```

Root UID inside this restricted worker does not supply a supported host.
No Docker, Podman, QEMU, or WSL executable is available. No fake `/proc`,
compiler substitute, or unisolated fallback was used for native validation.

## Commands and logs

Commands ran under `/workspace/scratch/cff1035d7206`, with Engine in
`mathcheck-engine`, build/test environment `.engine-closeout-venv`, consumer
environment `.engine-consumer-venv`, and outputs in `engine-closeout-20261004`.
The initial dependency setup installed the versions above and an editable
Engine with `--no-deps --no-build-isolation`. From the Engine checkout:

```sh
env -u LEAN_BIN ../.engine-closeout-venv/bin/python -m pytest tests -q -ra
env LEAN_BIN=/workspace/scratch/cff1035d7206/toolchains/lean-4.23.0-linux/bin/lean \
  LD_LIBRARY_PATH=/workspace/scratch/cff1035d7206/toolchains/lean-4.23.0-linux/lib/lean:/workspace/scratch/cff1035d7206/toolchains/lean-4.23.0-linux/lib \
  ../.engine-closeout-venv/bin/python -m pytest tests -q -ra \
  --basetemp=/workspace/scratch/cff1035d7206/engine-closeout-20261004/pytest-native
env SOURCE_DATE_EPOCH=1704067200 ../.engine-closeout-venv/bin/python -m build \
  --no-isolation --wheel --sdist --outdir ../engine-closeout-20261004/build-a
env SOURCE_DATE_EPOCH=1704067200 ../.engine-closeout-venv/bin/python -m build \
  --no-isolation --wheel --sdist --outdir ../engine-closeout-20261004/build-b
```

The fresh environment was created with `python -m venv`; its pip installed
`sympy==1.14.0` and `build-a/lean_kernel_verifier-0.3.3-py3-none-any.whl`.
From the output directory, outside the checkout:

```sh
../.engine-consumer-venv/bin/python -m pip check
env -u PYTHONPATH \
  LD_LIBRARY_PATH=/workspace/scratch/cff1035d7206/toolchains/lean-4.23.0-linux/lib/lean:/workspace/scratch/cff1035d7206/toolchains/lean-4.23.0-linux/lib \
  ../.engine-consumer-venv/bin/python consumer-controls.py
```

`consumer-controls.py` is the exact observation script, with paths for this
attempt and assertions for its known blocked host. It is **not a portable
release gate**. Its timeout helper is deliberately labelled non-Lean. The JSON
records every installed CLI request, expected result on a capable host, actual
result, command, and diagnostic. Controls include evaluate/count/sum/minimum,
the feasible-but-nonminimal minimum candidate 52, complete pairs, incomplete
pairs, and wrong cardinality. The actual minimum is 17 for that fixture.

Full logs are `source-tests.txt`, `native-tests.txt`, `build-a.txt`, `build-b.txt`,
`consumer-install.txt`, and `consumer-pip-check.txt`. Structured exit/status
records are `host-and-test-results.json` and `consumer-controls.json`.

## Candidate artifacts and publication

Both candidate wheels have SHA-256:

```
11dca4da84c56c4f045fe1e58c959db8a3d1490bdc6a78f4d97d4b871b45bca7
```

`artifact-hashes.json` also records both nonidentical source archive hashes.
`sdist-comparison.json` confirms identical contents for their 52 regular files.
Source archives are supplementary; the established GitHub distribution attaches
a wheel and release manifest. No repeatability claim is made for these source
archive bytes. Candidate binaries remain local and unpublished because the
required native gate failed to execute successfully.

The GitHub release collection was checked during this attempt: 0.3.2 remains
the latest published release and 0.3.3 is absent. Existing published assets were
not modified. No required/configured PyPI publication step was established.
GitHub source changes alone do not update installed packages.

For [Actions run 37129582149](https://github.com/stanleyngugi/mathcheck-engine/actions/runs/37129582149),
the API confirms the audited source SHA, zero steps, and runner ID 0. The user
supplied the separate signed-in billing-lock annotation; this connector cannot
fetch that annotations endpoint. That reason is reported provenance, not an
independently fetched annotation here. See `github-status.json`.

## Finite remaining closeout and RL handoff

1. Use a Linux host with real `/proc` and working bubblewrap namespaces, or a
   functioning suitable CI runner. Require the stock Lean 4.23.0 version probe
   and isolation probe to pass before counting native results.
2. Run the complete source suite with all ten required native/isolation entries
   enabled and no required skips. Require native positive controls to succeed
   and native negative controls to return `mathematical_rejection`; verify
   timeout, host-file/environment/network isolation, and fail-closed behavior.
3. Rebuild the exact selected release source, install its wheel into a fresh
   environment outside the checkout, and pass `pip check` plus installed
   isolated API/CLI controls, including candidate 52 and incomplete pairs.
4. Record exact source/toolchain/artifact evidence. Publish 0.3.3 by the existing
   wheel-and-manifest GitHub process only after the required checks pass, then
   verify the published release and downloaded artifact digests.

This update changes evidence only. Runtime and package metadata remain those
at `dce2fc88cee1e98ed3136ac89a4b40eba0d1ada7`, so it introduces no new dependency
pin requirement or API compatibility change. RL's current candidate pin is
still not a newly certified compatible release. Any later Engine runtime or
package-metadata change requires the RL agent to update immutable pins,
rebuild, and rerun joint native validation before publishing its Prime Hub
candidate. No Prime Hub publication was attempted here. No training or further
project expansion is required to close these gates.
