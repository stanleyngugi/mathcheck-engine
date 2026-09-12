# Supported computational verification contract (v0.3)

This package checks caller-supplied encoded claims. It neither solves arbitrary
natural-language mathematics nor authorizes a model's translation of prose.

| Interface | Input | Successful result |
|---|---|---|
| `verify_answer` | `ProblemSpec`, nonnegative integer candidate, runner | Exact supplied integer computation, count, sum or bounded minimum agrees |
| `verify_pair_certificate` | `PairCountSpec`, `PairCertificate`, runner | Entire finite satisfying relation equals the supplied list and count |
| `LeanCheckerRunner.run_source` | Lean source | Source passed configured checks and Lean; no prose or sandbox guarantee |

Prefer the first two interfaces for model-facing workflows: restricted expression
ASTs feed trusted source templates. The separate raw-source sanitizer is lexical,
not a Lean AST security proof. Symbolic discovery utilities propose candidates;
finite trace agreement cannot establish an infinite recurrence or general theorem.

`verified` is scoped by `scope`, `specification_digest` and, for pairs,
`certificate_digest`. `trust` includes native compiler/runtime trust; the name of
the package does not imply kernel-only reduction. Inspect `checker.timed_out`,
`backend_error`, output and return code before interpreting a failed check.
A toolchain failure is not evidence that a mathematical claim is false.
Structured results expose `status`: `checked_success`,
`mathematical_rejection`, or `operational_error`. Invalid and unsupported
requests are rejected before these structured APIs run.

Bounds are half-open nonnegative integers up to 1,000,000, with at most 10,000
values or pairs. Scalar answers must be in `[0, 10**1000)`; pair counts in
`[0, 10000]`. Expressions allow restricted integer arithmetic and predicates,
positive literal divisors, literal powers 0..16 without nested powers, at most
2,000 characters and 100 AST nodes. Sorted unique complete certificates are
required; merely supplying valid witnesses is insufficient.

The JSON stdin CLI exits 0 for a verified supplied claim, 1 for a failed checker
verdict, 2 for handled malformed requests; other operational failures can also
exit nonzero. It does not accept a natural-language problem or claim to certify
one. Use `python -m lean_kernel_verifier --lean-bin /absolute/path/to/lean`.

The pinned and tested toolchain is Lean 4.23.0. CLI checking is the default;
persistent diagnostics require CLI confirmation. The opt-in `lean-isolated`
Linux wrapper adds namespace/resource isolation and fails closed if unavailable.
It is not an audited multi-tenant deployment or aggregate-cgroup budget service.
Callers requiring exact reproducibility may set
`CheckerRunConfig(required_lean_version=(4, 23, 0))`; a mismatch is an
operational configuration failure.

Install and test independently of any solver checkout:

```bash
python -m pip install -e '.[dev]'
LEAN_BIN=/absolute/path/to/lean python -m pytest -q
```

No API credentials are required. A missing `LEAN_BIN` skips live checks, which is
not successful release validation. See README for isolated-runner configuration.
The post-release contract roadmap is recorded in `FUTURE_CONTRACTS.md`; those
families are extension targets, not capabilities claimed by v0.3.2.
