"""Real Lean checks. Set LEAN_BIN to enable; CI must provide it."""
import os
import unittest

from lean_kernel_verifier.runner.checker_runner import CheckerRunConfig, LeanCheckerRunner
from lean_kernel_verifier.sanitizer.template import build_checker_template


@unittest.skipUnless(os.environ.get('LEAN_BIN'), 'Set LEAN_BIN for real Lean integration tests')
class LiveLeanTests(unittest.TestCase):
    def test_correct_and_incorrect_observations(self):
        runner = LeanCheckerRunner(CheckerRunConfig(
            lean_executable=os.environ['LEAN_BIN'], timeout_seconds=120,
        ))
        try:
            for values, expected in (([1, 2, 3], True), ([1, 2, 4], False)):
                with self.subTest(values=values):
                    result = runner.run_source(build_checker_template(
                        'def f (n : Nat) : Nat := n + 1', values,
                    ))
                    self.assertEqual(result.success, expected, result.stdout + result.stderr)
                    self.assertFalse(result.timed_out)
        finally:
            runner.close()

    def test_multiline_formula_and_import(self):
        runner = LeanCheckerRunner(CheckerRunConfig(
            lean_executable=os.environ['LEAN_BIN'], timeout_seconds=120,
        ))
        try:
            result = runner.run_source(build_checker_template(
                'def f (n : Nat) : Nat :=\n  choose n 2', [0, 0, 1, 3, 6],
                extra_imports=['Init'],
            ))
            self.assertTrue(result.success, result.stdout + result.stderr)
        finally:
            runner.close()
