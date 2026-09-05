# Lean Kernel Verifier

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
candidate, compiler verdict, and explicit scope `encoded_specification_only`.

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

License: MIT for project code; see [LICENSE](LICENSE).
