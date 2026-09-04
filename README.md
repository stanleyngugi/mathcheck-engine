# Lean Kernel Verifier

A deterministic formal verification engine and symbolic recurrence kernel for Lean 4.

`lean-kernel-verifier` provides mathematical sequence verification, AST sanitization, trace consensus clustering, sequence degeneracy gating, and exact symbolic recurrence reconstruction without external LLM dependencies.

---

## Architecture Overview

```
lean_kernel_verifier/
├── core/                  # Data classes, S0–S8 pipeline contracts, failure taxonomy
├── runner/                # Lean 4 process orchestrator (sandboxing, timeouts, CLI/LSP)
├── sanitizer/             # AST & syntax sanitization, attribute stripping, template compiler
├── consensus/             # Prefix clustering, common prefix extraction, divergence gating
├── gating/                # Degeneracy detection, boundary condition & monotonicity holdouts
└── symbolic/              # Berlekamp-Massey over ℚ, Newton forward diff, Holonomic, Wu's method
```

### Core Subsystems

1. **Deterministic Runner (`runner/`)**
   - Sandboxed Lean 4 execution with strict timeout enforcement.
   - Preflight verification and Lean version compatibility checks (`>= 4.22.0`).
   - Anti-tautology validation ensuring Lean theorems explicitly verify formula vs expected evaluation.

2. **AST & Syntax Sanitizer (`sanitizer/`)**
   - AST validation and attribute stripping (`@[implemented_by]`, `@[extern]`, `@[csimp]`, `attribute [...]`).
   - Import allowlisting supporting configurable profiles (e.g., Profile A for pure `Init` environments, Profile B for mathlib tactics).
   - Safe theorem template compilation with proof contract enforcement.

3. **Trace Consensus Engine (`consensus/`)**
   - Prefix clustering across stochastic candidate traces.
   - Common prefix extraction and consensus cluster size thresholding (`min_cluster_size`).
   - Early divergence detection to eliminate spurious candidates before verification.

4. **Gating & Structural Degeneracy Checks (`gating/`)**
   - Natural problem constraint extraction: boundary conditions, monotonicity, divisibility, and non-negativity.
   - Structural sequence recognition: floor-affine loops, GCD-shift-mod sequences, and adversarial holdout validation.

5. **Exact Symbolic Kernel (`symbolic/`)**
   - **Berlekamp-Massey over $\mathbb{Q}$**: Exact linear recurrence discovery using rational arithmetic.
   - **Newton Forward Finite Differences**: Polynomial degree inference and integer binomial expansion.
   - **Holonomic Recurrence Fitting**: Rational parameter fitting for recurrences of the form $(w \cdot n + z) a_{n+1} = (u \cdot n + v) a_n$.
   - **Wu's Method**: Coordinate geometry characteristic set verification.

---

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

---

## Quickstart

### 1. Symbolic Recurrence Discovery (Berlekamp-Massey)

```python
from lean_kernel_verifier.symbolic.mining import run_berlekamp_massey, evaluate_candidate_at

# Fibonacci sequence: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, ...
terms = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
candidate = run_berlekamp_massey(terms, holdout_terms=3)

if candidate and candidate.holdout_passed:
    print(f"Recurrence discovered with order {candidate.degree}")
    # Predict next term
    next_val = evaluate_candidate_at(candidate, 12)
    print(f"a(12) = {next_val}")  # 144
```

### 2. Trace Consensus Clustering

```python
from lean_kernel_verifier.consensus.trace_consensus import select_consensus_trace
from lean_kernel_verifier.core.types import TraceSample

traces = [
    TraceSample(source_id=f"agent_{i}", values=(0, 1, 1, 2, 3, 5, 8, 13))
    for i in range(12)
]
# Add divergent traces
traces.append(TraceSample(source_id="faulty", values=(0, 1, 1, 2, 4, 7, 11, 18)))

result = select_consensus_trace(traces, min_cluster_size=10, prefix_terms=6)
if result.accepted:
    print(f"Consensus achieved across {result.cluster_size} traces: {result.consensus_trace}")
```

### 3. Lean 4 Theorem Sanitization and Execution

```python
from lean_kernel_verifier.sanitizer.template import compile_lean_check_source
from lean_kernel_verifier.runner.checker_runner import LeanCheckerRunner, CheckerRunConfig

source = compile_lean_check_source(
    formula_definition="def f (n : Nat) : Nat := n + 1",
    expected_values=[1, 2, 3, 4, 5],
)

runner = LeanCheckerRunner(CheckerRunConfig(timeout_seconds=10))
run_result = runner.run_source(source, sanitize_first=True)

if run_result.success:
    print("Formal Lean 4 verification succeeded!")
else:
    print(f"Verification failed: {run_result.stderr}")
```

---

## Running the Test Suite

```bash
pytest tests/
```

Or using standard `unittest`:

```bash
python -m unittest discover tests
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
