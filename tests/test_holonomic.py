import unittest

from lean_kernel_verifier.symbolic.holonomic_lite import (
    build_holonomic_lite_lean_definition,
    evaluate_holonomic_lite,
    find_holonomic_lite_candidate,
)


class HolonomicLiteTests(unittest.TestCase):
    def test_evaluate_factorial(self) -> None:
        # a(n) = n!, so a(n+1) = (n + 1) * a(n)
        # u=1, v=1, w=0, z=1
        seed = 1
        u, v, w, z = 1, 1, 0, 1
        expected = [1, 1, 2, 6, 24, 120, 720]
        for n, exp in enumerate(expected):
            self.assertEqual(evaluate_holonomic_lite(seed, u, v, w, z, n), exp)

    def test_find_factorial_candidate(self) -> None:
        trace = [1]
        for n in range(1, 12):
            trace.append(trace[-1] * n)
        candidate = find_holonomic_lite_candidate(
            trace,
            holdout_terms=3,
            adversarial_indices=[3, 6, 9],
            parameter_bound=12,
        )

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.kind, "holonomic_lite")
        self.assertTrue(candidate.holdout_passed)
        self.assertTrue(candidate.adversarial_passed)
        self.assertEqual(candidate.metadata["seed"], 1)

    def test_lean_definition_generation(self) -> None:
        lean_code = build_holonomic_lite_lean_definition(seed=1, u=1, v=1, w=0, z=1)
        self.assertIn("def f (n : Nat) : Nat :=", lean_code)
        self.assertIn("let seed : Nat := 1", lean_code)
        self.assertIn("build 0 seed (n + 1)", lean_code)

    def test_negative_parameters_raise(self) -> None:
        with self.assertRaises(ValueError):
            build_holonomic_lite_lean_definition(seed=-1, u=1, v=1, w=0, z=1)


if __name__ == "__main__":
    unittest.main()
