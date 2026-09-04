import unittest

from lean_kernel_verifier.sanitizer.sanitizer import SanitizerConfig, sanitize_source
from lean_kernel_verifier.sanitizer.template import build_checker_template, compile_lean_check_source


class SanitizerTests(unittest.TestCase):
    def test_strips_banned_attributes(self) -> None:
        source = """import Init
@[implemented_by foo] def x : Nat := 1
@[extern bar] theorem verify : True := by
  native_decide
"""
        result = sanitize_source(source, SanitizerConfig(profile="A", enforce_template_contract=False))
        self.assertTrue(result.passed)
        self.assertIn("implemented_by", result.stripped_attributes)
        self.assertIn("extern", result.stripped_attributes)
        self.assertNotIn("@[implemented_by", result.sanitized_source)
        self.assertNotIn("@[extern", result.sanitized_source)

    def test_strips_multiline_banned_attributes(self) -> None:
        source = """import Init
@[
  implemented_by foo_runtime
] def x : Nat := 1
@[
  extern bar_runtime
] theorem verify : True := by
  native_decide
@[
  csimp baz_runtime
] theorem aux : True := by
  trivial
"""
        result = sanitize_source(source, SanitizerConfig(profile="A", enforce_template_contract=False))
        self.assertTrue(result.passed)
        self.assertIn("implemented_by", result.stripped_attributes)
        self.assertIn("extern", result.stripped_attributes)
        self.assertIn("csimp", result.stripped_attributes)
        self.assertNotRegex(result.sanitized_source, r"@\[\s*implemented_by")
        self.assertNotRegex(result.sanitized_source, r"@\[\s*extern")
        self.assertNotRegex(result.sanitized_source, r"@\[\s*csimp")

    def test_rejects_attribute_command_bypass(self) -> None:
        source = """import Init
def fake (n : Nat) : Nat := 2 * n
def f (n : Nat) : Nat := n + 1000
attribute [implemented_by fake] f
theorem verify : True := by
  native_decide
"""
        result = sanitize_source(source, SanitizerConfig(profile="A", enforce_template_contract=False))
        self.assertFalse(result.passed)
        self.assertTrue(
            any("banned keyword `attribute`" in error for error in result.errors)
        )

    def test_rejects_disallowed_imports_in_profile_a(self) -> None:
        source = """import Mathlib.Tactic
theorem verify : True := by
  trivial
"""
        result = sanitize_source(source, SanitizerConfig(profile="A", enforce_template_contract=False))
        self.assertFalse(result.passed)
        self.assertTrue(any("not allowlisted" in error for error in result.errors))

    def test_template_compilation(self) -> None:
        compiled = compile_lean_check_source(
            formula_definition="def f (n : Nat) : Nat := n + 1",
            expected_values=[1, 2, 3],
        )
        self.assertIn("def f (n : Nat) : Nat := n + 1", compiled)
        self.assertIn("theorem verify :", compiled)
        self.assertIn("native_decide", compiled)


if __name__ == "__main__":
    unittest.main()
