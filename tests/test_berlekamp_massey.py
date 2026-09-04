import unittest
from fractions import Fraction
from unittest.mock import patch

from lean_kernel_verifier.symbolic import mining
from lean_kernel_verifier.symbolic.mining import (
    berlekamp_massey,
    build_bm_lean_definition,
    evaluate_bm_recurrence,
    evaluate_candidate_at,
    find_bm_candidate,
    find_smallest_integer_recurrence,
)


class BerlekampMasseyTests(unittest.TestCase):
    def test_fibonacci_recurrence(self) -> None:
        trace = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
        candidate = find_bm_candidate(
            trace,
            holdout_terms=3,
            adversarial_indices=[5, 8, 10],
        )
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.kind, "bm_recurrence")
        self.assertTrue(candidate.holdout_passed)
        self.assertTrue(candidate.adversarial_passed)
        self.assertEqual(candidate.metadata["coefficients"], [1, 1])
        self.assertEqual(evaluate_candidate_at(candidate, 11), 89)

    def test_rejects_insufficient_terms(self) -> None:
        short_trace = [0, 1, 1]
        candidate = find_bm_candidate(short_trace, holdout_terms=1)
        self.assertIsNone(candidate)

    def test_quasi_polynomial_with_negative_coefficients(self) -> None:
        def f(n: int) -> int:
            return sum(
                1
                for r in range(1, n + 1)
                for s in range(1, n + 1)
                if (r + 3 - 4 * s) % 12 == 0
            )

        trace = [f(n) for n in range(48)]
        coeffs = [int(c) for c in berlekamp_massey(trace[:44])]
        self.assertTrue(any(c < 0 for c in coeffs), "expected negative coefficients")

        candidate = find_bm_candidate(trace)
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.kind, "bm_recurrence")
        self.assertTrue(candidate.holdout_passed)
        self.assertTrue(candidate.adversarial_passed)
        self.assertEqual(evaluate_candidate_at(candidate, 100), 834)

    def test_lean_definition_generation(self) -> None:
        # Negative coefficients use Int core
        coeffs = [1, -1]
        seeds = [0, 1]
        source = build_bm_lean_definition(coeffs, seeds)
        self.assertIn("Array Int", source)
        self.assertIn("(- vals[(k - 2)]!)", source)
        self.assertTrue(source.startswith("def f (n : Nat) : Nat :="))

        # Non-negative coefficients use Nat core
        nat_source = build_bm_lean_definition([1, 1], seeds)
        self.assertIn("Array Nat", nat_source)
        self.assertNotIn("Array Int", nat_source)

    def test_smallest_integer_recurrence(self) -> None:
        fib = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
        self.assertEqual(find_smallest_integer_recurrence(fib), ([1, 1], 2))

        alternating = [0, 1, 0, 1, 0, 1, 0, 1]
        self.assertEqual(find_smallest_integer_recurrence(alternating), ([0, 1], 2))

        triangular = [0, 1, 3, 6, 10, 15, 21]
        self.assertEqual(find_smallest_integer_recurrence(triangular), ([3, -3, 1], 3))

    def test_fallback_to_integer_search_on_rational_fit(self) -> None:
        trace = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]

        def spurious_rational(sequence):
            return [Fraction(1, 2)]

        with patch.object(mining, "berlekamp_massey", spurious_rational):
            candidate = find_bm_candidate(trace)
            self.assertIsNotNone(candidate)
            assert candidate is not None
            self.assertEqual(candidate.metadata.get("recurrence_source"), "integer_recurrence_search")


if __name__ == "__main__":
    unittest.main()
