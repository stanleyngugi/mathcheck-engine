import math
import unittest

from lean_kernel_verifier.gating.structural import find_structural_candidate
from lean_kernel_verifier.gating.trace_checks import run_trace_vs_problem_checks
from lean_kernel_verifier.symbolic.mining import evaluate_candidate_at


class GatingAndStructuralTests(unittest.TestCase):
    def test_boundary_monotonicity_divisibility_pass(self) -> None:
        text = (
            "Given a(0)=2 and a(1)=4. The sequence is nondecreasing and each term is divisible by 2."
        )
        trace = [2, 4, 6, 8, 10]
        result = run_trace_vs_problem_checks(text, trace)

        self.assertTrue(result.passed)
        self.assertFalse(result.inconclusive)
        self.assertEqual(sorted(result.applied_checks), ["boundary", "divisibility", "monotonicity"])

    def test_checks_fail_on_mismatch(self) -> None:
        text = (
            "f(0)=1, f(1)=2. The sequence is strictly increasing and each term is divisible by 3."
        )
        trace = [1, 2, 2, 9, 12]
        result = run_trace_vs_problem_checks(text, trace)

        self.assertFalse(result.passed)
        self.assertFalse(result.inconclusive)
        self.assertFalse(result.monotonicity_passed)
        self.assertFalse(result.divisibility_passed)
        joined = " ".join(result.findings)
        self.assertIn("Monotonicity check failed", joined)
        self.assertIn("Divisibility check failed", joined)

    def test_inconclusive_when_no_deterministic_checks(self) -> None:
        result = run_trace_vs_problem_checks("Compute a(20).", [1, 2, 3, 4])
        self.assertTrue(result.inconclusive)
        self.assertFalse(result.passed)
        self.assertEqual(result.applied_checks, [])

    def test_counting_check_rejects_negative_trace(self) -> None:
        text = "How many ways are there to arrange the numbers 1..n?"
        result = run_trace_vs_problem_checks(text, [1, 2, -3, 4])
        self.assertFalse(result.passed)
        self.assertIn("counting_nonnegative", result.applied_checks)
        joined = " ".join(result.findings)
        self.assertIn("Counting check failed", joined)

    def test_detects_floor_affine(self) -> None:
        trace = [(n // 3) + 2 for n in range(16)]
        candidate = find_structural_candidate(
            trace,
            holdout_terms=4,
            adversarial_indices=[1, 5, 11, 14],
        )

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.kind, "structural")
        self.assertEqual(candidate.metadata["structural_kind"], "floor_affine")
        self.assertTrue(candidate.holdout_passed)
        self.assertTrue(candidate.adversarial_passed)
        self.assertEqual(evaluate_candidate_at(candidate, 15), 7)

    def test_detects_gcd_shift_mod(self) -> None:
        trace = [math.gcd(n + 1, 6) for n in range(16)]
        candidate = find_structural_candidate(
            trace,
            holdout_terms=4,
            adversarial_indices=[2, 7, 10, 15],
        )

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.metadata["structural_kind"], "gcd_shift_mod")
        self.assertTrue(candidate.holdout_passed)
        self.assertTrue(candidate.adversarial_passed)
        self.assertEqual(evaluate_candidate_at(candidate, 14), math.gcd(15, 6))


if __name__ == "__main__":
    unittest.main()
