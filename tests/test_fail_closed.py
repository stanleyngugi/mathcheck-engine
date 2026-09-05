import unittest
import subprocess
from unittest.mock import patch

from lean_kernel_verifier.sanitizer.sanitizer import SanitizerConfig, sanitize_source
from lean_kernel_verifier.sanitizer.template import build_checker_template
from lean_kernel_verifier.runner.checker_runner import (
    CheckerRunConfig, CheckerRunResult, LeanCheckerRunner,
)


class FailClosedTests(unittest.TestCase):
    def test_transient_preflight_timeout_can_recover(self):
        runner = LeanCheckerRunner()
        version = subprocess.CompletedProcess([], 0, 'Lean (version 4.23.0)', '')
        try:
            with patch('lean_kernel_verifier.runner.checker_runner.subprocess.run',
                       side_effect=[subprocess.TimeoutExpired('lean', 30), version]):
                self.assertIn('timed out', runner._ensure_lean_compatible())
                self.assertFalse(runner._preflight_checked)
                self.assertIsNone(runner._ensure_lean_compatible())
        finally:
            runner.close()

    def test_invalid_artifact_types_are_structured_failures(self):
        from lean_kernel_verifier.sanitizer.sanitizer import sanitize_artifact_dict
        for value in (None, [], {'schema_version': [], 'profile': {}, 'source': None},
                      {'schema_version': 'v1', 'profile': 'A', 'source': '', 'metadata': None}):
            with self.subTest(value=value):
                self.assertFalse(sanitize_artifact_dict(value).passed)

    def test_expected_literals_are_nonempty_naturals(self):
        for values in ([], [True], [1.5], [-1], ['1']):
            with self.subTest(values=values), self.assertRaises(ValueError):
                build_checker_template('def f (n : Nat) : Nat := n', values)

    def test_import_prefix_is_not_module_allowlist(self):
        result = sanitize_source('import InitMalicious', SanitizerConfig(enforce_template_contract=False))
        self.assertFalse(result.passed)

    def test_executable_commands_rejected(self):
        source = build_checker_template('def f (n : Nat) : Nat := n', [0, 1])
        for command in ('#eval IO.println "side effect"', 'initialize x : Nat ← pure 1',
                        'macro "bad" : tactic => `(tactic| trivial)'):
            with self.subTest(command=command):
                self.assertFalse(sanitize_source(source + '\n' + command).passed)

    def test_empty_lsp_diagnostics_cannot_override_cli_failure(self):
        runner = LeanCheckerRunner(CheckerRunConfig(execution_mode='persistent_server'))
        success = CheckerRunResult(True, 0, '', '', 0, False)
        failure = CheckerRunResult(False, 1, 'false theorem', '', 0, False)
        try:
            with patch.object(runner, '_run_persistent_backend', return_value=success), \
                 patch.object(runner, '_run_lean_file', return_value=failure) as cli:
                result = runner._run_checked_source(source='test', sanitizer_result=None)
            self.assertFalse(result.success)
            cli.assert_called_once()
        finally:
            runner.close()
