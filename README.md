# MathCheck Engine

**Bounded mathematical answers checked by generated Lean programs.**

The repository and public project name are **MathCheck Engine**. The published
Python distribution and import path remain `lean-kernel-verifier` and
`lean_kernel_verifier` in the 0.x series so existing integrations do not break.
See [BRANDING.md](BRANDING.md) for the naming and compatibility policy.

See [supported interfaces and result meanings](CAPABILITIES.md) for the v0.3
research contract and exact input limits.

See [future verification contracts](FUTURE_CONTRACTS.md) for the preserved,
non-blocking expansion plan across number theory, combinatorics, algebra, and
geometry.

The evidence-backed release narrative, including the 48/48 fixed computational
sweep, is in [TECHNICAL_ARTICLE.md](TECHNICAL_ARTICLE.md).
The current public release is
[`v0.3.2`](https://github.com/stanleyngugi/mathcheck-engine/releases/tag/v0.3.2),
supporting Python 3.11 through 3.13. Exact hashes and release-gate evidence are
recorded in [RELEASE_EVIDENCE_0.3.2.md](RELEASE_EVIDENCE_0.3.2.md).

Computational verification software: a Lean 4 subprocess runner, source checks,
finite sequence checking with `native_decide`, and exact recurrence discovery.
The Python symbolic routines also include polynomial interpolation, rational
Berlekamp–Massey, holonomic fitting, and Gröbner-based geometry checks.

## What a successful check means

The generated native theorem checks `f n == expected[n]` at each supplied index.
It proves agreement with that finite array. It does not prove that a sequence
continues forever, that the observations are correct, or that a natural-language
problem was translated correctly. Symbolic discovery and trace consensus are
proposal mechanisms, not universal proofs.

`native_decide` trusts Lean's compiler/runtime in addition to the kernel.
See the [Lean reference on proof validation](https://lean-lang.org/doc/reference/latest/ValidatingProofs/).
The project name does not imply kernel-only reduction.

The sanitizer uses lexical checks, not Lean's AST. The runner uses subprocess
timeouts, not an operating-system sandbox. Do not expose it as a service for
arbitrary untrusted Lean code without external process, filesystem, network,
and resource isolation. Profile B additionally needs a compatible Mathlib
installation; the automated native tests use Profile A and Lean 4.23.0.

## Install and test

```bash
python -m pip install -e '.[dev]'
python -m pytest tests -q
LEAN_BIN=/absolute/path/to/lean python -m pytest tests/test_live_lean.py -q
```

Lean is installed separately. `LEAN_BIN` enables real compiler tests. The
checkout includes a `lean-toolchain` pin. With elan installed, run
`elan toolchain install leanprover/lean4:v4.23.0` to provision it independently.
The suite skips those tests if `LEAN_BIN` is unset. The runner rejects versions below 4.22.0;
4.23.0 is the tested version. CLI execution is the default. Persistent mode is
optional and confirms successful LSP diagnostics with a completed CLI check.

## Example

The structured API accepts `ProblemSpec(kind, expression, start, stop)` for
integer evaluation, bounded sums, counts, and least-solution searches. Bounds
are half-open `[start, stop)`. Model output is parsed as restricted arithmetic,
then trusted templates generate Lean; arbitrary model-written Lean is unnecessary.
`verify_answer(spec, candidate, runner)` returns the specification digest,
candidate, compiler verdict, explicit status, and scope
`encoded_specification_only`. Backend failures and timeouts are
`operational_error`, not mathematical rejection.

```python
from lean_kernel_verifier.specification import ProblemSpec, verify_answer
from lean_kernel_verifier.runner.checker_runner import LeanCheckerRunner

runner = LeanCheckerRunner()
try:
    result = verify_answer(ProblemSpec('count', 'x%3 == 0', 1, 100), 33, runner)
    print(result.verified)
finally:
    runner.close()
```

For a runnable checked-success and checked-rejection walkthrough, see
[`examples/bounded_count.py`](examples/bounded_count.py).

The command `python -m lean_kernel_verifier --lean-bin /path/to/lean` accepts a
JSON object on stdin with `specification` and `answer` fields. It exits nonzero
on invalid input or failed verification. No HTTP service or OS sandbox is claimed.

```python
from lean_kernel_verifier.runner.checker_runner import CheckerRunConfig, LeanCheckerRunner
from lean_kernel_verifier.sanitizer.template import build_checker_template
from lean_kernel_verifier.symbolic.mining import find_bm_candidate, evaluate_candidate_at

candidate = find_bm_candidate([0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89], holdout_terms=3)
assert candidate is not None and candidate.holdout_passed
assert evaluate_candidate_at(candidate, 12) == 144

runner = LeanCheckerRunner(CheckerRunConfig(lean_executable="lean"))
try:
    source = build_checker_template("def f (n : Nat) : Nat := n + 1", [1, 2, 3])
    result = runner.run_source(source)
    print(result.success, result.stdout, result.stderr)
finally:
    runner.close()
```

See [AUDIT.md](AUDIT.md) for findings, verification, and remaining work.

## Complete bounded-pair certificates

`PairCountSpec` extends checking to predicates over two bounded nonnegative
integers, with at most 10,000 pairs. `PairCertificate` contains a sorted, unique
list and a claimed count. Lean checks equality with the **entire** satisfying
relation and checks its length. A list containing only some valid witnesses is
rejected. Completeness is relative to the stated finite bounds, not an unbounded
problem or the original prose.

```python
from lean_kernel_verifier.certificates import PairCountSpec, PairCertificate, verify_pair_certificate

spec = PairCountSpec('x < y and x+y == 4', 0, 5, 0, 5)
certificate = PairCertificate(((0, 4), (1, 3)), answer=2)
# Use your configured runner; close it when finished.
result = verify_pair_certificate(spec, certificate, runner)
```

The result binds both specification and certificate digests and reports scope
`encoded_bounded_pair_count_with_complete_enumeration`. It does not claim a
general combinatorics prover or remove the compiler/runtime trust assumption.
The verifier CLI also accepts `{"specification": {"kind": "count_pairs", ...},
"pairs": [[0, 4], [1, 3]], "answer": 2}`. Extra request fields are rejected.

## Opt-in Linux isolation

Installing the package provides the `lean-isolated` executable. Configure a
standalone Lean 4.23.0 distribution and use this as the CLI checker executable:

```bash
export LKV_SANDBOX_TOOLCHAIN=/path/to/lean-4.23.0-linux
lean-isolated --version
```

Set `CheckerRunConfig(lean_executable="lean-isolated", timeout_seconds=210)`.
Linux `bubblewrap`, `prlimit`, and usable namespaces are required. Failure to
isolate or a mismatched Lean version is fatal; there is no direct-execution
fallback. The wrapper supports one source file or `--version`, not LSP/Mathlib
project execution. Environment variables and home/project directories are hidden;
system libraries and the pinned distribution are read-only, while a copied source
file and scratch directories are writable. Network and process namespaces are
separate. The configured distribution and mounted system libraries remain trusted.

Limits: 2 GiB address space and 120 CPU seconds per process, 150 seconds wall time
for compilation plus a 30-second version check, 16 MiB per output file, 128 file
descriptors, and 256 KiB returned diagnostics. These are not aggregate cgroup
limits: fork-heavy workloads or many small files need additional deployment
controls. Use a dedicated worker account/container and disk/process/memory quotas
before multi-tenant deployment. A host killing the wrapper abruptly can leave
scratch directories; provision a bounded scratch filesystem and a cleanup policy.
This is an opt-in isolation layer, not an audited production security guarantee.

`toolchain_identity(root)` in `lean_kernel_verifier.isolation` records the Lean
binary SHA-256 for audit logs. It is explicitly not an attestation or fingerprint
of the entire compiler, library, and operating-system dependency chain.

License: MIT for project code; see [LICENSE](LICENSE).
