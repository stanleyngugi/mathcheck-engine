import os
import unittest

from lean_kernel_verifier.specification import ProblemSpec, compile_answer_check, verify_answer
from lean_kernel_verifier.runner.checker_runner import CheckerRunConfig, LeanCheckerRunner


class SpecificationTests(unittest.TestCase):
    def test_injection_and_unsupported_expressions_are_rejected(self):
        for expression in ('__import__("os")', 'x.__class__', 'answer', 'True', '1/2',
                           '2**100', '(2**16)**16', 'x//0', 'x%(-2)', 'x+x'):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                ProblemSpec('evaluate', expression)

    def test_bounds_are_explicit_and_limited(self):
        for bounds in ((-1, 1), (2, 1), (0, 10001), (True, 3)):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                ProblemSpec('sum', 'x', *bounds)

    def test_digest_binds_spec_but_not_candidate(self):
        spec = ProblemSpec('count', 'x%3 == 0', 1, 100)
        self.assertNotEqual(spec.digest, ProblemSpec('count', 'x%3 == 0', 1, 101).digest)
        for candidate in (33, 34):
            source = compile_answer_check(spec, candidate)
            self.assertIn(f'problem_spec {candidate}', source)
            self.assertIn('native_decide', source)


@unittest.skipUnless(os.environ.get('LEAN_BIN'), 'Set LEAN_BIN to compile specification checks')
class LiveSpecificationTests(unittest.TestCase):
    def test_all_specification_kinds_and_negative_controls(self):
        runner = LeanCheckerRunner(CheckerRunConfig(lean_executable=os.environ['LEAN_BIN'], timeout_seconds=120))
        cases = [
            (ProblemSpec('evaluate', '(7**5 - 3)//2 % 97'), 60),
            (ProblemSpec('count', 'x%3 == 0 and x%5 != 0', 1, 31), 8),
            (ProblemSpec('sum', 'x*x-2*x', 2, 9), 133),
            (ProblemSpec('minimum', 'x%7 == 3 and x%5 == 2', 0, 100), 17),
            (ProblemSpec('sum', 'x', 4, 4), 0),
        ]
        try:
            for spec, answer in cases:
                for candidate, expected in ((answer, True), (answer + 1, False)):
                    with self.subTest(kind=spec.kind, candidate=candidate):
                        result = verify_answer(spec, candidate, runner)
                        self.assertEqual(result.verified, expected, result.checker.stdout + result.checker.stderr)
                        self.assertFalse(result.checker.timed_out)
                        self.assertEqual(result.scope, 'encoded_specification_only')
        finally:
            runner.close()
