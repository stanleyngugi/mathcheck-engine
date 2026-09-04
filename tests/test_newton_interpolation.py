import unittest

from lean_kernel_verifier.symbolic.mining import (
    detect_polynomial_degree,
    evaluate_candidate_at,
    evaluate_newton_polynomial,
    find_polynomial_candidate,
    finite_difference_table,
    newton_forward_coefficients,
)


class NewtonInterpolationTests(unittest.TestCase):
    def test_finite_difference_table(self) -> None:
        seq = [0, 1, 4, 9, 16]
        table = finite_difference_table(seq)
        self.assertEqual(table[0], [0, 1, 4, 9, 16])
        self.assertEqual(table[1], [1, 3, 5, 7])
        self.assertEqual(table[2], [2, 2, 2])
        self.assertEqual(table[3], [0, 0])

    def test_detect_polynomial_degree(self) -> None:
        linear = [2 * n + 5 for n in range(10)]
        self.assertEqual(detect_polynomial_degree(linear), 1)

        quadratic = [n * n + 3 * n + 2 for n in range(10)]
        self.assertEqual(detect_polynomial_degree(quadratic), 2)

        cubic = [n**3 - n for n in range(12)]
        self.assertEqual(detect_polynomial_degree(cubic), 3)

    def test_polynomial_candidate_quadratic(self) -> None:
        trace = [n * n + 2 * n + 1 for n in range(12)]
        candidate = find_polynomial_candidate(
            trace,
            holdout_terms=3,
            adversarial_indices=[3, 7, 10],
            max_degree=6,
        )

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.kind, "polynomial")
        self.assertTrue(candidate.holdout_passed)
        self.assertTrue(candidate.adversarial_passed)
        self.assertEqual(evaluate_candidate_at(candidate, 12), 169)

    def test_newton_forward_coefficients_evaluation(self) -> None:
        # f(n) = n(n-1)/2 + 2n + 3
        # n=0: 3
        # n=1: 5
        # n=2: 8
        # n=3: 12
        seq = [3, 5, 8, 12, 17]
        coeffs = newton_forward_coefficients(seq, degree=2)
        self.assertEqual(coeffs, [3, 2, 1])
        for idx, val in enumerate(seq):
            self.assertEqual(evaluate_newton_polynomial(coeffs, idx), val)
        self.assertEqual(evaluate_newton_polynomial(coeffs, 5), 23)

    def test_rejects_non_polynomial(self) -> None:
        exp_trace = [2**n for n in range(10)]
        # Exponential is not a low-degree polynomial
        deg = detect_polynomial_degree(exp_trace, max_degree=4)
        self.assertIsNone(deg)


if __name__ == "__main__":
    unittest.main()
