from __future__ import annotations

import math
from typing import Iterable, Sequence

from ..core.types import FormulaCandidate


def find_structural_candidate(
    trace: Sequence[int],
    *,
    holdout_terms: int = 4,
    adversarial_indices: Iterable[int] | None = None,
) -> FormulaCandidate | None:
    if len(trace) < 6:
        return None
    if any(value < 0 for value in trace):
        return None

    floor = _detect_floor_affine(trace)
    if floor is not None:
        divisor, offset = floor
        holdout_idx = _holdout_indices(len(trace), holdout_terms)
        adv_idx = _normalize_indices(adversarial_indices, len(trace))
        holdout_passed = all(
            _eval_floor_affine(idx, divisor, offset) == trace[idx] for idx in holdout_idx
        )
        adversarial_passed = all(
            _eval_floor_affine(idx, divisor, offset) == trace[idx] for idx in adv_idx
        )
        return FormulaCandidate(
            kind="structural",
            lean_definition=(
                "def f (n : Nat) : Nat :=\n"
                f"  (n / {divisor}) + {offset}"
            ),
            holdout_passed=holdout_passed,
            adversarial_passed=adversarial_passed,
            metadata={
                "structural_kind": "floor_affine",
                "divisor": divisor,
                "offset": offset,
                "holdout_indices": holdout_idx,
                "adversarial_indices": adv_idx,
            },
        )

    gcd_model = _detect_gcd_shift_mod(trace)
    if gcd_model is not None:
        shift, modulus = gcd_model
        holdout_idx = _holdout_indices(len(trace), holdout_terms)
        adv_idx = _normalize_indices(adversarial_indices, len(trace))
        holdout_passed = all(
            _eval_gcd_shift(idx, shift, modulus) == trace[idx] for idx in holdout_idx
        )
        adversarial_passed = all(
            _eval_gcd_shift(idx, shift, modulus) == trace[idx] for idx in adv_idx
        )
        return FormulaCandidate(
            kind="structural",
            lean_definition=(
                "def f (n : Nat) : Nat :=\n"
                f"  Nat.gcd (n + {shift}) {modulus}"
            ),
            holdout_passed=holdout_passed,
            adversarial_passed=adversarial_passed,
            metadata={
                "structural_kind": "gcd_shift_mod",
                "shift": shift,
                "modulus": modulus,
                "holdout_indices": holdout_idx,
                "adversarial_indices": adv_idx,
            },
        )

    affine_gcd_model = _detect_affine_gcd(trace)
    if affine_gcd_model is not None:
        scale, shift, modulus, offset = affine_gcd_model
        holdout_idx = _holdout_indices(len(trace), holdout_terms)
        adv_idx = _normalize_indices(adversarial_indices, len(trace))
        holdout_passed = all(
            _eval_affine_gcd(idx, scale, shift, modulus, offset) == trace[idx]
            for idx in holdout_idx
        )
        adversarial_passed = all(
            _eval_affine_gcd(idx, scale, shift, modulus, offset) == trace[idx]
            for idx in adv_idx
        )
        return FormulaCandidate(
            kind="structural",
            lean_definition=(
                "def f (n : Nat) : Nat :=\n"
                f"  Nat.gcd ({scale} * n + {shift}) {modulus} + {offset}"
            ),
            holdout_passed=holdout_passed,
            adversarial_passed=adversarial_passed,
            metadata={
                "structural_kind": "gcd_affine",
                "scale": scale,
                "shift": shift,
                "modulus": modulus,
                "offset": offset,
                "holdout_indices": holdout_idx,
                "adversarial_indices": adv_idx,
            },
        )

    valuation_model = _detect_valuation(trace)
    if valuation_model is not None:
        prime, shift, offset = valuation_model
        holdout_idx = _holdout_indices(len(trace), holdout_terms)
        adv_idx = _normalize_indices(adversarial_indices, len(trace))
        holdout_passed = all(
            _eval_valuation(idx, prime, shift, offset) == trace[idx] for idx in holdout_idx
        )
        adversarial_passed = all(
            _eval_valuation(idx, prime, shift, offset) == trace[idx] for idx in adv_idx
        )
        return FormulaCandidate(
            kind="structural",
            lean_definition=(
                "def vPow (p n : Nat) : Nat :=\n"
                "  if p <= 1 then 0\n"
                "  else\n"
                "    let rec go (m acc fuel : Nat) : Nat :=\n"
                "      match fuel with\n"
                "      | 0 => acc\n"
                "      | fuel' + 1 =>\n"
                "          if m == 0 then acc\n"
                "          else if m % p == 0 then go (m / p) (acc + 1) fuel'\n"
                "          else acc\n"
                "    go n 0 (n + 1)\n\n"
                "def f (n : Nat) : Nat :=\n"
                f"  vPow {prime} (n + {shift}) + {offset}"
            ),
            holdout_passed=holdout_passed,
            adversarial_passed=adversarial_passed,
            metadata={
                "structural_kind": "valuation_shift",
                "prime": prime,
                "shift": shift,
                "offset": offset,
                "holdout_indices": holdout_idx,
                "adversarial_indices": adv_idx,
            },
        )

    return None


def _detect_floor_affine(trace: Sequence[int]) -> tuple[int, int] | None:
    for divisor in range(2, 11):
        offset = trace[0]
        if offset < 0:
            continue
        if all(_eval_floor_affine(idx, divisor, offset) == value for idx, value in enumerate(trace)):
            return divisor, offset
    return None


def _detect_gcd_shift_mod(trace: Sequence[int]) -> tuple[int, int] | None:
    max_modulus = min(30, max(2, max(trace) + 1))
    for modulus in range(2, max_modulus + 1):
        for shift in range(0, modulus + 1):
            if all(_eval_gcd_shift(idx, shift, modulus) == value for idx, value in enumerate(trace)):
                return shift, modulus
    return None


def _detect_affine_gcd(trace: Sequence[int]) -> tuple[int, int, int, int] | None:
    max_modulus = min(40, max(2, max(trace) + 8))
    for scale in range(1, 5):
        for modulus in range(2, max_modulus + 1):
            for shift in range(0, modulus + 1):
                baseline = math.gcd(scale * 0 + shift, modulus)
                if trace[0] < baseline:
                    continue
                offset = trace[0] - baseline
                if all(
                    _eval_affine_gcd(idx, scale, shift, modulus, offset) == value
                    for idx, value in enumerate(trace)
                ):
                    return scale, shift, modulus, offset
    return None


def _detect_valuation(trace: Sequence[int]) -> tuple[int, int, int] | None:
    for prime in (2, 3, 5):
        for shift in range(0, 8):
            if trace[0] < _v_p(shift, prime):
                continue
            offset = trace[0] - _v_p(shift, prime)
            if all(_eval_valuation(idx, prime, shift, offset) == value for idx, value in enumerate(trace)):
                return prime, shift, offset
    return None


def _eval_floor_affine(n: int, divisor: int, offset: int) -> int:
    return (n // divisor) + offset


def _eval_gcd_shift(n: int, shift: int, modulus: int) -> int:
    return math.gcd(n + shift, modulus)


def _eval_affine_gcd(n: int, scale: int, shift: int, modulus: int, offset: int) -> int:
    return math.gcd((scale * n) + shift, modulus) + offset


def _eval_valuation(n: int, prime: int, shift: int, offset: int) -> int:
    return _v_p(n + shift, prime) + offset


def _v_p(value: int, prime: int) -> int:
    if value <= 0 or prime <= 1:
        return 0
    count = 0
    current = value
    while current % prime == 0:
        current //= prime
        count += 1
    return count


def _holdout_indices(length: int, holdout_terms: int) -> list[int]:
    terms = max(0, min(holdout_terms, length - 3))
    return list(range(length - terms, length))


def _normalize_indices(indices: Iterable[int] | None, length: int) -> list[int]:
    if indices is None:
        return []
    return sorted({idx for idx in indices if 0 <= idx < length})
