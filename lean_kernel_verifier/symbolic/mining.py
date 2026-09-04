from __future__ import annotations

from fractions import Fraction
import math
from math import comb
from textwrap import dedent
from typing import Iterable, Sequence

from ..core.types import FormulaCandidate


def finite_difference_table(sequence: Sequence[int]) -> list[list[int]]:
    if not sequence:
        return []
    rows: list[list[int]] = [list(sequence)]
    while len(rows[-1]) > 1:
        prev = rows[-1]
        rows.append([prev[i + 1] - prev[i] for i in range(len(prev) - 1)])
    return rows


def detect_polynomial_degree(sequence: Sequence[int], max_degree: int = 8) -> int | None:
    if len(sequence) < 3:
        return None
    table = finite_difference_table(sequence)
    for degree in range(1, min(max_degree, len(table) - 1) + 1):
        row = table[degree]
        if row and all(value == row[0] for value in row):
            return degree
    return None


def newton_forward_coefficients(sequence: Sequence[int], degree: int) -> list[int]:
    table = finite_difference_table(sequence)
    return [table[i][0] for i in range(degree + 1)]


def evaluate_newton_polynomial(coefficients: Sequence[int], n: int) -> int:
    total = 0
    for i, coeff in enumerate(coefficients):
        total += coeff * comb(n, i)
    return total


def build_polynomial_lean_definition(coefficients: Sequence[int], function_name: str = "f") -> str:
    expr = build_polynomial_expression(coefficients, "n")
    return f"def {function_name} (n : Nat) : Nat :=\n  {expr}"


def build_polynomial_expression(coefficients: Sequence[int], variable_name: str) -> str:
    if any(value < 0 for value in coefficients):
        raise ValueError("Negative polynomial coefficients are not supported for Nat formulas.")

    terms: list[str] = []
    for i, coeff in enumerate(coefficients):
        if coeff == 0:
            continue
        if i == 0:
            terms.append(str(coeff))
            continue
        choose_term = f"choose {variable_name} {i}"
        terms.append(choose_term if coeff == 1 else f"({coeff} * {choose_term})")

    return " + ".join(terms) if terms else "0"


def find_polynomial_candidate(
    trace: Sequence[int],
    *,
    holdout_terms: int = 4,
    adversarial_indices: Iterable[int] | None = None,
    max_degree: int = 8,
) -> FormulaCandidate | None:
    if len(trace) < 6:
        return None

    holdout_terms = max(0, min(holdout_terms, len(trace) - 3))
    train_end = len(trace) - holdout_terms
    train = list(trace[:train_end])
    degree = detect_polynomial_degree(train, max_degree=max_degree)
    if degree is None:
        return None

    coefficients = newton_forward_coefficients(train, degree)
    if any(value < 0 for value in coefficients):
        return None

    holdout_idx = list(range(train_end, len(trace)))
    holdout_passed = all(
        evaluate_newton_polynomial(coefficients, idx) == trace[idx] for idx in holdout_idx
    )
    adv_idx = _normalize_indices(adversarial_indices, len(trace))
    adversarial_passed = all(
        evaluate_newton_polynomial(coefficients, idx) == trace[idx] for idx in adv_idx
    )

    lean_definition = build_polynomial_lean_definition(coefficients)
    return FormulaCandidate(
        kind="polynomial",
        lean_definition=lean_definition,
        holdout_passed=holdout_passed,
        adversarial_passed=adversarial_passed,
        metadata={
            "degree": degree,
            "coefficients": coefficients,
            "train_terms": len(train),
            "holdout_indices": holdout_idx,
            "adversarial_indices": adv_idx,
        },
    )


def berlekamp_massey(sequence: Sequence[int]) -> list[Fraction]:
    """Return recurrence coefficients r_i for s[n] = Σ r_i s[n-i-1]."""
    if not sequence:
        return []

    c = [Fraction(1)]
    b = [Fraction(1)]
    linear_complexity = 0
    shift = 1
    discrepancy_scale = Fraction(1)

    for n in range(len(sequence)):
        discrepancy = Fraction(sequence[n])
        for i in range(1, linear_complexity + 1):
            discrepancy += c[i] * Fraction(sequence[n - i])

        if discrepancy == 0:
            shift += 1
            continue

        prev = c[:]
        factor = -discrepancy / discrepancy_scale
        if len(c) < len(b) + shift:
            c.extend([Fraction(0)] * (len(b) + shift - len(c)))
        for i in range(len(b)):
            c[i + shift] += factor * b[i]

        if 2 * linear_complexity <= n:
            linear_complexity = n + 1 - linear_complexity
            b = prev
            discrepancy_scale = discrepancy
            shift = 1
        else:
            shift += 1

    return [-c[i] for i in range(1, linear_complexity + 1)]


def evaluate_bm_recurrence(coefficients: Sequence[int], seeds: Sequence[int], n: int) -> int:
    order = len(coefficients)
    if n < order:
        return seeds[n]

    values = list(seeds)
    while len(values) <= n:
        k = len(values)
        next_value = 0
        for offset, coeff in enumerate(coefficients, start=1):
            next_value += coeff * values[k - offset]
        values.append(next_value)
    return values[n]


def _solve_exact_unique_linear_system(
    rows: list[list[Fraction]],
    rhs: list[Fraction],
) -> list[Fraction] | None:
    """Exact Gaussian elimination over QQ for the unique-solution case.

    Returns the solution vector, or None when the system is inconsistent or
    rank-deficient (an underdetermined fit is rejected: a recurrence with
    free parameters is not pinned by the training evidence).
    """
    if not rows:
        return None
    col_count = len(rows[0])
    augmented = [list(row) + [value] for row, value in zip(rows, rhs)]
    row_count = len(augmented)
    pivot_cols: list[int] = []
    row_index = 0
    for col in range(col_count):
        pivot = next(
            (r for r in range(row_index, row_count) if augmented[r][col] != 0),
            None,
        )
        if pivot is None:
            continue
        augmented[row_index], augmented[pivot] = augmented[pivot], augmented[row_index]
        pivot_value = augmented[row_index][col]
        augmented[row_index] = [value / pivot_value for value in augmented[row_index]]
        for r in range(row_count):
            if r != row_index and augmented[r][col] != 0:
                factor = augmented[r][col]
                augmented[r] = [
                    a - factor * b for a, b in zip(augmented[r], augmented[row_index])
                ]
        pivot_cols.append(col)
        row_index += 1
        if row_index == row_count:
            break
    for r in range(row_index, row_count):
        if augmented[r][col_count] != 0 and all(v == 0 for v in augmented[r][:col_count]):
            return None
    if len(pivot_cols) < col_count:
        return None
    solution = [Fraction(0)] * col_count
    for r, col in enumerate(pivot_cols):
        solution[col] = augmented[r][col_count]
    return solution


def find_smallest_integer_recurrence(
    sequence: Sequence[int],
    *,
    max_order: int = 64,
) -> tuple[list[int], int] | None:
    """Search for the smallest integer-coefficient linear recurrence.

    For each order L = 1..min(max_order, len(sequence)//2), solve the Hankel
    system s[n] = sum(r_i * s[n-i]) exactly over QQ using every available
    equation, and accept the first L whose unique solution is integral.
    """
    n_terms = len(sequence)
    cap = min(max_order, n_terms // 2)
    for order in range(1, cap + 1):
        rows = [
            [Fraction(sequence[n - i]) for i in range(1, order + 1)]
            for n in range(order, n_terms)
        ]
        rhs = [Fraction(sequence[n]) for n in range(order, n_terms)]
        solution = _solve_exact_unique_linear_system(rows, rhs)
        if solution is None:
            continue
        if any(value.denominator != 1 for value in solution):
            continue
        return [int(value) for value in solution], order
    return None


def build_bm_lean_definition(
    coefficients: Sequence[int],
    seeds: Sequence[int],
    function_name: str = "f",
) -> str:
    if not coefficients:
        raise ValueError("BM coefficients cannot be empty.")
    if any(value < 0 for value in seeds):
        raise ValueError("Negative BM seeds are not supported for Nat formulas.")

    order = len(coefficients)
    if len(seeds) < order:
        raise ValueError("Seed count must be at least recurrence order.")

    seed_literal = ", ".join(str(v) for v in seeds[:order])

    def term(value_term: str, coeff: int, int_mode: bool) -> str:
        if coeff == 1:
            return value_term
        if coeff == -1 and int_mode:
            return f"(- {value_term})"
        if coeff < 0:
            return f"(- ({abs(coeff)} * {value_term}))"
        return f"({coeff} * {value_term})"

    if all(value >= 0 for value in coefficients):
        terms = [
            term(f"vals[(k - {idx})]!", coeff, int_mode=False)
            for idx, coeff in enumerate(coefficients, start=1)
            if coeff != 0
        ]
        recurrence_expr = " + ".join(terms) if terms else "0"
        return dedent(
            f"""
            def {function_name} (n : Nat) : Nat :=
              let seeds : Array Nat := #[{seed_literal}]
              let order : Nat := {order}
              if n < order then
                seeds[n]!
              else
                let rec build (k : Nat) (vals : Array Nat) (fuel : Nat) : Array Nat :=
                  match fuel with
                  | 0 => vals
                  | fuel' + 1 =>
                      if k > n then
                        vals
                      else
                        let next : Nat := {recurrence_expr}
                        build (k + 1) (vals.push next) fuel'
                let vals := build order seeds (n + 1)
                vals[n]!
            """
        ).strip()

    terms = [
        term(f"vals[(k - {idx})]!", coeff, int_mode=True)
        for idx, coeff in enumerate(coefficients, start=1)
        if coeff != 0
    ]
    recurrence_expr = " + ".join(terms) if terms else "0"
    return dedent(
        f"""
        def {function_name} (n : Nat) : Nat :=
          let seeds : Array Int := #[{seed_literal}]
          let order : Nat := {order}
          if n < order then
            (seeds[n]!).toNat
          else
            let rec build (k : Nat) (vals : Array Int) (fuel : Nat) : Array Int :=
              match fuel with
              | 0 => vals
              | fuel' + 1 =>
                  if k > n then
                    vals
                  else
                    let next : Int := {recurrence_expr}
                    build (k + 1) (vals.push next) fuel'
            let vals := build order seeds (n + 1)
            (vals[n]!).toNat
        """
    ).strip()


def find_bm_candidate(
    trace: Sequence[int],
    *,
    holdout_terms: int = 4,
    adversarial_indices: Iterable[int] | None = None,
    max_order: int = 64,
) -> FormulaCandidate | None:
    if len(trace) < 6:
        return None

    holdout_terms = max(0, min(holdout_terms, len(trace) - 3))
    train_end = len(trace) - holdout_terms
    train = list(trace[:train_end])
    coeffs_frac = berlekamp_massey(train)
    order = len(coeffs_frac)
    if order == 0:
        return None

    if len(train) < 2 * order:
        return None

    recurrence_source = "berlekamp_massey"
    if any(coeff.denominator != 1 for coeff in coeffs_frac):
        found = find_smallest_integer_recurrence(train, max_order=max_order)
        if found is None:
            return None
        coefficients, order = found
        recurrence_source = "integer_recurrence_search"
    else:
        coefficients = [int(coeff) for coeff in coeffs_frac]

    if len(train) < 2 * order:
        return None

    seeds = train[:order]
    if any(value < 0 for value in seeds):
        return None

    recurrence_ok = all(
        evaluate_bm_recurrence(coefficients, seeds, idx) == train[idx]
        for idx in range(order, len(train))
    )
    if not recurrence_ok:
        return None

    holdout_idx = list(range(train_end, len(trace)))
    holdout_passed = all(
        evaluate_bm_recurrence(coefficients, seeds, idx) == trace[idx] for idx in holdout_idx
    )
    adv_idx = _normalize_indices(adversarial_indices, len(trace))
    adversarial_passed = all(
        evaluate_bm_recurrence(coefficients, seeds, idx) == trace[idx] for idx in adv_idx
    )

    lean_definition = build_bm_lean_definition(coefficients, seeds)
    return FormulaCandidate(
        kind="bm_recurrence",
        lean_definition=lean_definition,
        holdout_passed=holdout_passed,
        adversarial_passed=adversarial_passed,
        metadata={
            "order": order,
            "coefficients": coefficients,
            "seeds": seeds,
            "train_terms": len(train),
            "holdout_indices": holdout_idx,
            "adversarial_indices": adv_idx,
            "recurrence_source": recurrence_source,
        },
    )


def evaluate_candidate_at(candidate: FormulaCandidate, n: int) -> int | None:
    if candidate.kind == "polynomial":
        coeffs = candidate.metadata.get("coefficients")
        if isinstance(coeffs, list) and all(isinstance(x, int) for x in coeffs):
            return evaluate_newton_polynomial(coeffs, n)
        return None

    if candidate.kind == "bm_recurrence":
        coeffs = candidate.metadata.get("coefficients")
        seeds = candidate.metadata.get("seeds")
        if (
            isinstance(coeffs, list)
            and isinstance(seeds, list)
            and all(isinstance(x, int) for x in coeffs)
            and all(isinstance(x, int) for x in seeds)
        ):
            return evaluate_bm_recurrence(coeffs, seeds, n)
        return None

    if candidate.kind == "case_split":
        modulus = candidate.metadata.get("modulus")
        cases = candidate.metadata.get("cases")
        if not isinstance(modulus, int) or modulus <= 0 or not isinstance(cases, list):
            return None
        residue = n % modulus
        q = n // modulus
        for case in cases:
            if not isinstance(case, dict) or case.get("residue") != residue:
                continue
            coeffs = case.get("coefficients")
            if isinstance(coeffs, list) and all(isinstance(x, int) for x in coeffs):
                return evaluate_newton_polynomial(coeffs, q)
        return None

    if candidate.kind == "modular_cycle":
        period = candidate.metadata.get("period")
        pattern = candidate.metadata.get("pattern")
        if (
            isinstance(period, int)
            and period > 0
            and isinstance(pattern, list)
            and len(pattern) == period
            and all(isinstance(x, int) and x >= 0 for x in pattern)
        ):
            return pattern[n % period]
        return None

    if candidate.kind == "holonomic_lite":
        seed = candidate.metadata.get("seed")
        u = candidate.metadata.get("u")
        v = candidate.metadata.get("v")
        w = candidate.metadata.get("w")
        z = candidate.metadata.get("z")
        if all(isinstance(x, int) and x >= 0 for x in (seed, u, v, w, z)):
            value = int(seed)
            for i in range(n):
                den = (int(w) * i) + int(z)
                if den == 0:
                    return None
                num = ((int(u) * i) + int(v)) * value
                if num % den != 0:
                    return None
                value = num // den
            return value
        return None

    if candidate.kind in {"structural", "oeis"}:
        kind = candidate.metadata.get("structural_kind")
        if kind == "special_constant":
            value = candidate.metadata.get("constant_value")
            if isinstance(value, int):
                return value
            return None
        if kind == "floor_affine":
            divisor = candidate.metadata.get("divisor")
            offset = candidate.metadata.get("offset")
            if isinstance(divisor, int) and divisor > 0 and isinstance(offset, int) and offset >= 0:
                return (n // divisor) + offset
            return None
        if kind == "gcd_shift_mod":
            shift = candidate.metadata.get("shift")
            modulus = candidate.metadata.get("modulus")
            if isinstance(shift, int) and shift >= 0 and isinstance(modulus, int) and modulus >= 1:
                return math.gcd(n + shift, modulus)
            return None
        if kind == "gcd_affine":
            scale = candidate.metadata.get("scale")
            shift = candidate.metadata.get("shift")
            modulus = candidate.metadata.get("modulus")
            offset = candidate.metadata.get("offset")
            if (
                isinstance(scale, int)
                and scale >= 0
                and isinstance(shift, int)
                and shift >= 0
                and isinstance(modulus, int)
                and modulus >= 1
                and isinstance(offset, int)
                and offset >= 0
            ):
                return math.gcd((scale * n) + shift, modulus) + offset
            return None
        if kind == "valuation_shift":
            prime = candidate.metadata.get("prime")
            shift = candidate.metadata.get("shift")
            offset = candidate.metadata.get("offset")
            if (
                isinstance(prime, int)
                and prime > 1
                and isinstance(shift, int)
                and shift >= 0
                and isinstance(offset, int)
                and offset >= 0
            ):
                return _v_p(n + shift, prime) + offset
            return None
        if kind == "multiplicative_power_law":
            exponent = candidate.metadata.get("exponent")
            if isinstance(exponent, int) and exponent >= 0:
                return n**exponent
            return None
        if kind == "multiplicative_constant_one":
            return 0 if n == 0 else 1
        if kind == "oeis_recurrence":
            seeds = candidate.metadata.get("seeds")
            coeffs_oeis = candidate.metadata.get("coefficients")
            if (
                isinstance(coeffs_oeis, list)
                and isinstance(seeds, list)
                and all(isinstance(x, int) for x in coeffs_oeis)
                and all(isinstance(x, int) for x in seeds)
            ):
                return evaluate_bm_recurrence(coeffs_oeis, seeds, n)
            return None
        coeffs = candidate.metadata.get("coefficients")
        if isinstance(coeffs, list) and all(isinstance(x, int) for x in coeffs):
            return evaluate_newton_polynomial(coeffs, n)
    if candidate.kind == "multiplicative":
        kind = candidate.metadata.get("structural_kind")
        if kind == "multiplicative_power_law":
            exponent = candidate.metadata.get("exponent")
            if isinstance(exponent, int) and exponent >= 0:
                return n**exponent
        if kind == "multiplicative_constant_one":
            return 0 if n == 0 else 1
    return None


def _normalize_indices(indices: Iterable[int] | None, length: int) -> list[int]:
    if indices is None:
        return []
    out = sorted({idx for idx in indices if 0 <= idx < length})
    return out


def _v_p(value: int, prime: int) -> int:
    if value <= 0 or prime <= 1:
        return 0
    count = 0
    current = value
    while current % prime == 0:
        current //= prime
        count += 1
    return count
