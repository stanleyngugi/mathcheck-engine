# Lean Kernel Verifier: bounded computation with explicit claims

## Abstract

Lean Kernel Verifier v0.3 checks bounded, caller-supplied computational claims.
It accepts a restricted specification and candidate answer, constructs Lean 4
source from trusted templates, and records whether the encoded equality was
accepted. It also checks complete bounded pair certificates: the supplied pairs
must equal the entire satisfying relation, not merely be valid witnesses.

This is deliberately narrower than a general theorem prover. A successful result
does not establish that natural-language prose was translated faithfully, and
`native_decide` adds the Lean compiler and runtime to the trusted computing base.
Within that contract, the implementation and its finite scale sweep are complete.

## The interface is the claim

The main scalar interface is `verify_answer(ProblemSpec, candidate, runner)`.
`ProblemSpec` describes one of four computations over a half-open nonnegative
integer domain: expression evaluation, finite sum, bounded count, or bounded
minimum. The expression parser permits a small arithmetic and predicate language;
arbitrary model-written Python or Lean is not executed.

The pair interface is
`verify_pair_certificate(PairCountSpec, PairCertificate, runner)`. The certificate
contains sorted unique pairs and a claimed count. Lean reconstructs the bounded
satisfying relation and checks exact equality with the supplied list as well as
its length. A partial list of valid examples therefore fails.

Successful results bind the specification digest, candidate, scope, and checker
record. Operational failures such as timeouts are kept separate from mathematical
rejection. The command-line interface uses the same contract and exits nonzero on
failed or malformed claims.

## Bounds and trust

The v0.3 contract permits bounds up to 1,000,000 but at most 10,000 enumerated
values or pairs per claim. Scalar answers are nonnegative integers below
`10**1000`; pair counts are at most 10,000. Expressions are limited to 2,000
characters, 100 AST nodes, positive literal divisors, and literal powers from 0
through 16 without nested powers.

Lean 4.23.0 is pinned and tested. CLI checking is the default. The optional
`lean-isolated` wrapper adds Linux namespaces, read-only toolchain mounts, and
resource limits; it fails closed when those controls are unavailable. It is not
an audited public multi-tenant sandbox. The compiler/runtime trust required by
`native_decide` is accepted and reported rather than presented as an unresolved
defect.

## Validation evidence

The release validation ran with actual Lean, not a mocked compiler:

- 68 tests and 38 subtests passed with zero skips.
- The original 48-case computational sweep passed 44 cases. Four 10,000-pair
  certificates exceeded the 120-second limit.
- The fixed sweep passed 48/48 with no operational failures. Total recorded time
  was 19.97 seconds, the median case took 0.405 seconds, and the slowest took
  0.621 seconds.

The pair fix moved decoding and validation of large pair data into Lean instead
of elaborating a huge list literal. It did not weaken the completeness obligation.
Both records remain in `evaluation_records/`: the original sweep took 591.40
seconds and preserves all four timeouts; the fixed record preserves the successful
replacement measurement.

## What the result does and does not mean

The verifier establishes an exact bounded computation for the supplied encoded
specification under the documented trust assumptions. It can reject a wrong
integer, a malformed expression, an incomplete pair list, or a checker failure
without converting any of those outcomes into success.

It does not prove that an LLM encoded the original question correctly, extend a
finite recurrence to all indices, solve arbitrary algebra or geometry, or remove
native compiler trust. Those boundaries make the result useful: downstream
systems can state exactly which claim ran, which executable checked it, and which
failure occurred without inflating a computational check into a universal proof.

## Reproduction

Install the project with its development dependencies, provision Lean 4.23.0,
and run:

```bash
LEAN_BIN=/absolute/path/to/lean python -m pytest tests -q
```

The machine-readable sweep records are
`evaluation_records/public_v1_computational_sweep.jsonl` and
`evaluation_records/public_v1_computational_sweep_fixed.jsonl`. See
`CAPABILITIES.md` for the normative input and result contract.
