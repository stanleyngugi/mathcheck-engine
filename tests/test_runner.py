import unittest
from unittest.mock import patch

from lean_kernel_verifier.runner.checker_runner import CheckerRunConfig, LeanCheckerRunner
from lean_kernel_verifier.sanitizer.sanitizer import SanitizerConfig
from lean_kernel_verifier.sanitizer.template import build_checker_template


class CheckerRunnerTests(unittest.TestCase):
    def test_missing_lean_binary_returns_structured_error(self) -> None:
        runner = LeanCheckerRunner(CheckerRunConfig(lean_executable="__missing_lean_binary__"))
        source = build_checker_template(
            formula_definition="def f (n : Nat) : Nat := n + 1",
            expected_values=[1, 2, 3],
        )
        result = runner.run_source(source, sanitize_first=True)

        self.assertFalse(result.success)
        self.assertIn("not found", result.stderr)
        self.assertFalse(result.timed_out)

    def test_sanitizer_failure_short_circuits(self) -> None:
        runner = LeanCheckerRunner(CheckerRunConfig(lean_executable="__missing_lean_binary__"))
        source = "import Mathlib.Tactic\ntheorem verify : True := by\n  native_decide\n"
        result = runner.run_source(
            source,
            SanitizerConfig(profile="A", enforce_template_contract=False),
            sanitize_first=True,
        )

        self.assertFalse(result.success)
        self.assertIn("not allowlisted", result.stderr)
        self.assertIsNotNone(result.sanitizer_result)

    def test_sanitizer_bypass_is_rejected(self) -> None:
        runner = LeanCheckerRunner(CheckerRunConfig(lean_executable="__missing_lean_binary__"))
        source = build_checker_template(
            formula_definition="def f (n : Nat) : Nat := n + 1",
            expected_values=[1, 2, 3],
        )
        result = runner.run_source(source, sanitize_first=False)

        self.assertFalse(result.success)
        self.assertIn("Sanitization bypass is disallowed", result.stderr)

    def test_incompatible_lean_version_is_rejected(self) -> None:
        class FakeCompletedProcess:
            def __init__(self) -> None:
                self.returncode = 0
                self.stdout = "Lean (version 4.21.0, x86_64-unknown-linux-gnu, Release)\n"
                self.stderr = ""

        runner = LeanCheckerRunner(CheckerRunConfig(lean_executable="lean"))
        source = build_checker_template(
            formula_definition="def f (n : Nat) : Nat := n + 1",
            expected_values=[1, 2, 3],
        )
        with patch("lean_kernel_verifier.runner.checker_runner.subprocess.run", return_value=FakeCompletedProcess()):
            result = runner.run_source(source, sanitize_first=True)

        self.assertFalse(result.success)
        self.assertIn("below required >= 4.22.0", result.stderr)
        self.assertTrue(result.backend_error)

    def test_exact_lean_version_can_be_required(self) -> None:
        class FakeCompletedProcess:
            returncode = 0
            stdout = "Lean (version 4.24.0, x86_64-unknown-linux-gnu, Release)\n"
            stderr = ""

        runner = LeanCheckerRunner(CheckerRunConfig(
            lean_executable="lean", required_lean_version=(4, 23, 0),
        ))
        source = build_checker_template(
            formula_definition="def f (n : Nat) : Nat := n + 1",
            expected_values=[1, 2, 3],
        )
        with patch("lean_kernel_verifier.runner.checker_runner.subprocess.run", return_value=FakeCompletedProcess()):
            result = runner.run_source(source)
        self.assertFalse(result.success)
        self.assertTrue(result.backend_error)
        self.assertIn("does not match required version 4.23.0", result.stderr)

    def test_tautological_native_verify_statement_is_rejected_before_preflight(self) -> None:
        runner = LeanCheckerRunner(CheckerRunConfig(lean_executable="__missing_lean_binary__"))
        source = build_checker_template(
            formula_definition="def f (n : Nat) : Nat := n + 1",
            expected_values=[1, 2, 3],
        )
        source = source.replace("= true := by", "= true || True := by")
        result = runner.run_source(source, sanitize_first=True)

        self.assertFalse(result.success)
        self.assertIn("must prove formula-vs-expected equality", result.stderr)
        self.assertNotIn("not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
