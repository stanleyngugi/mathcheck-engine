# Verification audit — 2026-09-05

## Assessment

This is a usable research foundation for computational verification. It is not
yet a production service or a guarantee of correct answers to arbitrary prose
problems. The structured API provides the clearest boundary: a bounded integer
specification, a proposed answer, and a Lean compiler verdict about that pair.

## Changes verified in this audit

- Corrected template indentation: interpolated multiline declarations previously
  broke Lean layout while text-only tests still passed.
- Rejected empty observation arrays, Boolean/float pseudo-integers, malformed
  artifact types, executable command directives, and misleading import prefixes.
- Made CLI completion the default acceptance path. Persistent LSP diagnostics
  now require CLI confirmation before a successful verdict; a quiet interval is
  not an elaboration-completion signal.
- Added configurable, retryable version-probe timeouts. A transient timeout no
  longer permanently poisons a runner.
- Replaced geometry `sympify` of external expressions with a restricted AST
  arithmetic parser. Witness checks use exact rationals and require all coordinates.
- Added `ProblemSpec`, a deterministic source compiler, `verify_answer`, and a
  JSON stdin CLI. Supported operations are evaluation, bounded count, bounded sum,
  and bounded minimum; candidate answers never enter the expression parser.
- Added real Lean positive and negative controls, malformed input tests, and
  regression coverage of the LSP acceptance boundary.
- Corrected unsupported AST-sanitizer, OS-sandbox, and kernel-only claims.

## Evidence and reproduction

Tests use Python 3.12, SymPy 1.14.0, pytest 9.1.1, and Lean 4.23.0 on Linux/WSL.
The final compiler-enabled run passed 55 tests and 38 subtests with no skips.

```bash
python -m pip install -e '.[dev]'
LEAN_BIN=/absolute/path/to/lean python -m pytest tests -q
python -m pip wheel --no-deps .
```

`test_live_lean.py` compiles correct and wrong observation arrays and multiline
formulas. `test_specification.py` compiles all four operations with correct and
deliberately wrong candidates, including empty sums. These tests skip explicitly
without `LEAN_BIN`; an offline-only pass must not be reported as a compiler pass.
The audit also builds wheels and tests imports outside the source checkouts.

## Boundaries that remain

1. A specification can faithfully compute the wrong interpretation. Hashes bind
   the supplied specification to a verdict; they do not establish semantic fidelity.
2. Native evaluation trusts Lean's compiler/runtime in addition to its kernel.
   See [Lean's proof-validation reference](https://lean-lang.org/doc/reference/latest/ValidatingProofs/).
3. Finite observations cannot establish a recurrence at unseen indices or prove
   arbitrary universal claims. Symbolic routines propose candidates; they are
   separate from the Lean-checking trust boundary.
4. The raw-source sanitizer is lexical, not an AST parser or an OS sandbox.
   The structured API generates source from a constrained arithmetic grammar;
   exposing arbitrary raw Lean remains inappropriate without external isolation.
5. CLI confirmation sacrifices the previous claimed persistent-worker speedup.
   No sub-second latency claim has been established by this audit. Startup and
   mounted-filesystem costs were significant under concurrent machine load.
6. Profile B/Mathlib, other platforms and Lean versions, and production concurrency
   have not received the same live coverage as Profile A/Lean 4.23.0.

## Recommended next milestones

Implement a trustworthy persistent completion protocol with differential CLI
tests before optimizing throughput. Extend certificate forms only with paired
positive/negative controls and explicit domains. Add isolated workers and resource
limits before a network service. Measure statement-checking accuracy separately
from natural-language translation accuracy and deployment latency.

## Follow-up: complete pair certificates and opt-in isolation (0.2.0)

PairCountSpec accepts bounded predicates over x and y, with at most 10,000 pairs.
The generated native theorem checks exact equality of the supplied sorted unique
list with the full satisfying relation and checks its claimed count. Specification
and certificate digests are retained. Valid-but-incomplete witnesses, wrong counts,
and constraint-violating pairs are negative controls, not successes. This is only
completeness within the encoded rectangle, not unbounded mathematical completeness
or natural-language fidelity.

The lean-isolated CLI uses bubblewrap namespaces, cleared environment, read-only
system/toolchain mounts, a fresh source workspace, and explicit resource/output
limits. Missing isolation tools, inaccessible namespaces, or a wrong Lean version
fail closed. Live probes check that host files and environment variables are
hidden and that the network namespace differs from the host. A live model-driven
pair certificate was also accepted through this isolated wrapper.

Initial live testing exposed a malformed Lean template and a test-probe IO type
annotation error; both were corrected. Some early live runs timed out under
variable machine load and were not counted as validation successes. The isolation
limits were not relaxed to obtain a pass. Binary fingerprints identify the Lean
executable only, not the full trusted compilation/runtime dependency chain.

Isolation is opt-in, CLI-only, and not an audited multi-tenant security guarantee.
Per-process rlimits are not aggregate cgroups; deployments still need process,
memory, and scratch-disk quotas and cleanup. The native compiler/runtime and
configured toolchain/system libraries remain trusted.

Final 0.2.0 validation passed 63 tests and 38 subtests without skips, including
real certificate controls, sandbox probes, and CLI routing. After mounted-storage
timeouts, the pinned release archive was extracted onto Linux storage. The Lean
executable and main shared-library SHA-256 hashes matched the original installation;
the same test limits passed in approximately 54 seconds. This comparison does not
fingerprint the entire dependency chain and is not a general throughput benchmark.
Fresh installed-wheel checks imported all 114 modules across both packages and
confirmed their 0.2.0 versions and the solver's verifier dependency constraint.

## Follow-up: parameter-varying negative controls

Two additional seeded live tests perform 56 Lean checks independently of any
word-problem benchmark. They vary signed division/modulo, nonzero bounds, sums,
counts, leastness, and finite pair relations. Correct answers and complete
certificates pass; adjacent wrong answers, omitted satisfying pairs, and wrong
cardinalities fail. Both tests passed on pinned Lean 4.23.0 without timeouts.
The existing full suite separately passed 63 tests and 38 subtests in this cycle.
These tests extend regression evidence, not a proof that the implementation has
no bugs or that arbitrary problem translations are faithful. Runtime code and
the native compiler/runtime trust boundary are unchanged.
