# Future verification contracts roadmap

Status: post-0.3.2 roadmap. None of the items in this document blocks the
bounded 0.3.2 verifier or the MathCheck RL 0.2.1 release.

## Purpose

Lean Kernel Verifier is intended to be a general, extensible computational
verification foundation. Its runner, isolation, result taxonomy, evidence
binding, and trusted-template architecture can support many domains. The
currently audited structured contract library is smaller: exact integer
evaluation, bounded integer sums and counts, bounded least solutions, and
complete relations over bounded integer pairs.

This document preserves the intended expansion path without claiming that an
unimplemented family already works. A successful Lean execution establishes
the encoded proposition. It does not by itself establish that an English
problem was translated faithfully, and an integer-valued final answer does not
imply that the underlying mathematics is an integer-expression problem.

## Current structured meaning

An explicitly bounded integer contract has all of the following properties:

- the environment fixes an expression or predicate before seeing the candidate;
- variables range over declared finite half-open intervals such as
  `0 <= x < 1000`;
- the current implementation evaluates at most 10,000 values or pairs;
- the model supplies only a nonnegative integer candidate, or a sorted complete
  pair certificate and count;
- a trusted template checks the whole declared finite domain in Lean;
- success is scoped to the exact encoded specification and its digest;
- timeout, toolchain, isolation, and backend failures remain operational errors,
  never mathematical counterexamples.

Examples supported by the current structured API include:

- `evaluate`: check that a closed restricted integer expression equals 137;
- `sum`: check that 12,340 is the sum of `x*x + 3*x` for every integer in a
  declared finite interval;
- `count`: check that 167 integers in a declared interval satisfy a modular
  predicate;
- `minimum`: check that a candidate satisfies a predicate and that every
  smaller integer in the interval fails it;
- `count_pairs`: check that a submitted list is exactly the complete satisfying
  relation over a declared finite integer rectangle, with the claimed length.

The pair contract is not merely witness checking. If one valid pair is omitted,
the ordered-list equality with the complete computed relation fails.

## Competition-mathematics coverage today

The four common olympiad and competition categories describe the subject of a
problem, not the form of its verification certificate. Many problems have an
integer final answer while relying on real geometry, an unbounded theorem,
polynomial structure, or an exponentially large combinatorial object.

| Domain | What the current structured contracts can check | Important missing contracts |
| --- | --- | --- |
| Number theory | Bounded divisibility and congruence predicates, exact bounded counts and sums, least solutions within a fixed interval, and bounded two-variable Diophantine relations expressible in the restricted AST | Primality/factorization certificates, efficient modular exponentiation, gcd/lcm primitives, unbounded Diophantine arguments, Pell-type certificates, valuation reasoning, and general universal theorems |
| Combinatorics | Exact bounded counts over one integer variable and complete relations over two finite integer axes; small encodings reducible to these forms | Native schemas for subsets, permutations, sequences, graphs, matchings, colorings, paths, recurrences, dynamic-programming tables, bijections, and compact counting certificates |
| Algebra | Exact closed integer expressions, bounded polynomial-like sums, bounded integer roots or minima expressible with the restricted arithmetic grammar | Exact rational and algebraic candidates, symbolic polynomial identity/factorization, systems of equations, inequalities over rationals/reals, matrices, resultants, Gröbner or Nullstellensatz certificates, and functional equations |
| Geometry | Problems already reduced by a trusted source to small bounded integer-coordinate searches or pair relations | Exact rational/algebraic coordinates, incidence and orientation predicates, non-degeneracy, squared-distance and area contracts, intersection construction, polynomial-system certificates, diagram-to-specification authority, and synthetic proof obligations |

Consequently, confidence in the current release is high for its declared finite
integer contracts, not for arbitrary problems sampled from all four categories.
Number theory and small finite combinatorics are the closest current fit.
Integer-valued algebra is a partial fit. Geometry is supported only after a
trusted reduction to the current integer contract; the existing symbolic
geometry discovery utilities are proposal mechanisms, not final reward
authority.

## Required shape of every future contract

Each new family should implement a common conceptual interface, whether or not
the Python API eventually uses these exact method names:

1. `parse_specification`: validate an environment-owned immutable target.
2. `parse_candidate`: accept only the artifact the model is permitted to choose.
3. `estimate_cost`: reject domains or certificates outside explicit limits
   before Lean execution.
4. `compile_trusted_check`: generate the authoritative proposition from trusted
   templates rather than treating candidate source as the target.
5. `scope`: state exactly what a successful result establishes.
6. `evidence`: bind specification, candidate/certificate, toolchain, limits, and
   execution result digests.
7. `classify_result`: distinguish checked success, mathematical rejection,
   invalid input, unsupported task, and operational error.

Every contract requires paired honest/wrong candidates, malformed inputs,
boundary limits, timeout/backend controls, and a family-specific shortcut test.
Contracts involving optimality, uniqueness, or completeness must check those
properties explicitly; checking feasibility alone is insufficient.

## Phase A: high-leverage finite contracts

### Bounded tuples and finite-set enumeration

Generalize the pair relation to a small fixed number of typed integer variables.
The specification declares each finite axis and a predicate. The candidate
submits a canonical complete tuple set and count. Reject duplicate, unordered,
out-of-domain, incomplete, and predicate-violating tuples.

This would cover more bounded Diophantine, combinatorial configuration, and
small coordinate-search problems without introducing a candidate-controlled
checker.

Done condition: exact full-relation equality, product-size cost limit, canonical
serialization, digest binding, and adversarial omission/duplication tests.

### Bounded optimization and argmin/argmax

The environment declares a feasible predicate, objective, finite domain, and
tie policy. The candidate supplies an objective value and one or all optimizers,
as the contract requires. Lean checks feasibility, objective evaluation, global
optimality over the complete domain, and tie completeness.

Done condition: a feasible-but-suboptimal witness, a correct value with a wrong
witness, and an omitted tied optimizer all fail.

### Number-theory primitives

Add restricted, costed support for absolute value, gcd, lcm, bounded modular
exponentiation, divisibility, and possibly integer valuations. Avoid exposing
arbitrary recursion through the expression grammar.

Done condition: exact Lean semantics match independent Python controls across
boundary and randomized cases, with explicit operand and exponent limits.

### Exact rational candidates

Represent rationals canonically as signed numerator and positive denominator in
lowest terms. Add exact rational evaluation, sum, comparison, and bounded
optimization without floating-point conversion.

Done condition: equivalent noncanonical forms are normalized or rejected by a
documented rule; zero denominators, sign ambiguity, overflow/resource attacks,
and approximate decimal substitutions fail closed.

### Polynomial identity and factorization certificates

The environment declares a polynomial over a supported exact coefficient ring.
Candidates may supply a canonical coefficient vector, factorization, quotient,
or remainder certificate. Lean checks multiplication or coefficient equality,
degree and coefficient bounds, and any required irreducibility claim under a
separate contract.

Done condition: sampled-point agreement is never substituted for an exact
identity; unit factors, ordering, multiplicity, and coefficient-domain rules are
canonical and tested.

## Phase B: combinatorial object contracts

### Permutations, subsets, and sequences

Introduce bounded canonical encodings for permutations, combinations, finite
sequences, partitions, and assignments. Candidate artifacts must be type- and
domain-correct before a mathematical predicate runs.

These schemas enable direct verification of schedules, orderings, colorings,
small extremal examples, and constructive combinatorics.

### Graph certificates

Specify a finite graph independently of the model. Candidate certificates may
include paths, cycles, trees, matchings, flows, cuts, colorings, or complete
enumerations. Each certificate type needs its own completeness or optimality
obligation.

For example, a maximum matching contract cannot accept a large matching merely
because it is valid; it also needs a checked optimality certificate or an exact
bounded search.

### Dynamic-programming and recurrence certificates

Allow the environment to define finite states, base cases, transitions, and a
target state. A candidate table or trace is checked at every state and bound to
the declared recurrence. This can verify large finite counts more efficiently
than enumerating every object when the recurrence is independently authoritative.

Finite recurrence agreement must not be advertised as proof of an infinite
sequence theorem without a separate induction contract.

### SAT/SMT-style proof objects

For suitably encoded finite constraints, accept independently checkable proof
objects or unsatisfiability certificates. External solvers may propose them, but
Lean or a small verified checker remains the final authority. Solver exit status
alone is not a verification result.

## Phase C: algebra and geometry contracts

### Exact algebraic numbers

Represent an algebraic number by an integer polynomial, an isolating rational
interval, and a root-selection rule. Equality, ordering, and arithmetic require
checked separation and nonzero-denominator obligations.

This is substantially safer than accepting floating-point approximations, but
it introduces meaningful proof and performance work.

### Matrices and finite linear algebra

Add exact matrices over integers, modular rings, and rationals. Candidate
contracts may cover multiplication, determinant, rank witnesses, inverses,
linear-system solutions, and eigenvalue claims only where exact certificate
semantics are defined.

### Coordinate geometry

The environment declares points, lines, circles, incidence constraints,
non-degeneracy assumptions, and the requested invariant using exact coordinates
or algebraic-number certificates. Candidate coordinates or scalar answers are
checked against all declared constraints.

This verifies the encoded coordinate formulation. Faithful translation from an
original diagram or prose remains an upstream responsibility and must retain
provenance and review evidence.

### Polynomial-system certificates

Explore exact resultants, Gröbner bases, and Nullstellensatz-style certificates
for systems arising in algebra and coordinate geometry. The current symbolic
modules may propose candidates, but a future trusted contract must check the
certificate, coefficient domain, non-degeneracy conditions, and the precise
logical conclusion in Lean.

### Certified interval bounds

For problems whose result is an inequality or a uniquely rounded integer,
accept rational interval certificates with directed error bounds. Never use an
ordinary floating-point result as final authority. The rounding or uniqueness
condition must be part of the checked proposition.

## Phase D: environment-fixed theorem and project contracts

A separate advanced interface may accept a model-produced proof term or tactic
script only after the environment freezes the exact theorem statement, imports,
options, and project revision. This is conventional proof generation, not the
candidate-only computational contract used by native-verify.

Supporting Mathlib projects requires a stronger project sandbox, dependency
lock, filesystem policy, build cache policy, and aggregate resource controls.
It must not be presented as equivalent to the current one-file Profile A
wrapper.

## Suggested priority for competition coverage

If the objective is broad competition-mathematics usefulness, implement in this
order:

1. number-theory primitives and exact rational candidates;
2. bounded tuple/set and optimization contracts;
3. permutations, subsets, graphs, and dynamic-programming certificates;
4. exact polynomial identity/factorization and finite linear algebra;
5. exact algebraic-number and coordinate-geometry contracts;
6. checked polynomial-system and certified-interval certificates;
7. optional environment-fixed theorem proving with a stronger project sandbox.

This order expands useful exact verification while preserving small, auditable
candidate languages. Geometry comes later because an integer final answer often
hides real or algebraic constructions and semantic translation obligations.

## Non-goals and stopping discipline

- Do not require support for all mathematics before releasing a bounded family.
- Do not treat a category label such as “algebra” as a verification contract.
- Do not make the candidate model the authority for its own target.
- Do not replace exact identity or completeness with a few sampled tests.
- Do not call an operational failure a mathematical rejection.
- Do not claim arbitrary prose fidelity from a successful encoded check.
- Do not expand bounds without an explicit cost and isolation review.
- Do not make this roadmap a retroactive blocker for the tested 0.3.2 release.

The durable goal is a growing registry of precisely scoped contracts sharing one
verification and evidence foundation—not a single interface that ambiguously
claims to verify every form of mathematics.
