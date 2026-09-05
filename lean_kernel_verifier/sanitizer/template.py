from __future__ import annotations

from textwrap import dedent
from typing import Iterable, Sequence

THEOREM_MODE_NATIVE = "native_decide"
THEOREM_MODE_GRIND = "grind"


def build_checker_template(
    formula_definition: str,
    expected_values: Sequence[int],
    theorem_mode: str = THEOREM_MODE_NATIVE,
    max_rec_depth: int = 10000,
    max_heartbeats: int = 0,
    extra_imports: Iterable[str] | None = None,
    grind_goal: str | None = None,
) -> str:
    imports = " ".join(extra_imports or [])
    import_line = f"import {imports}\n" if imports else ""
    expected_literal = _lean_nat_array_literal(expected_values)

    theorem_block: str
    if theorem_mode == THEOREM_MODE_NATIVE:
        theorem_block = dedent(
            """
            theorem verify :
              (Array.range expected.size).all (fun n => f n == expected[n]!) = true := by
              native_decide
            """
        ).strip()
    elif theorem_mode == THEOREM_MODE_GRIND:
        if not grind_goal:
            raise ValueError("`grind_goal` is required when theorem_mode='grind'.")
        theorem_block = dedent(
            f"""
            theorem verify : {grind_goal} := by
              grind
            """
        ).strip()
    else:
        raise ValueError(f"Unsupported theorem_mode: {theorem_mode}")

    template = dedent(
        f"""
        set_option maxRecDepth {max_rec_depth}
        set_option maxHeartbeats {max_heartbeats}

        def powMod (base exp mod : Nat) : Nat :=
          if mod == 0 then 0
          else if mod == 1 then 0
          else
            let rec loop (b e acc fuel : Nat) : Nat :=
              match fuel with
              | 0 => acc
              | fuel' + 1 =>
                  if e == 0 then acc
                  else
                    let acc' := if e % 2 == 1 then (acc * b) % mod else acc
                    loop ((b * b) % mod) (e / 2) acc' fuel'
            loop (base % mod) exp 1 (exp + 1)

        def factorial : Nat → Nat
          | 0 => 1
          | n + 1 => (n + 1) * factorial n

        def choose (n k : Nat) : Nat :=
          if k > n then 0
          else
            let k := min k (n - k)
            let rec loop (i acc fuel : Nat) : Nat :=
              match fuel with
              | 0 => acc
              | fuel' + 1 =>
                  if i >= k then acc
                  else loop (i + 1) (acc * (n - i) / (i + 1)) fuel'
            loop 0 1 (k + 1)

        """
    ).strip()
    return (
        import_line + template + "\n\n" + formula_definition.strip()
        + f"\n\ndef expected : Array Nat := {expected_literal}\n\n"
        + theorem_block + "\n"
    )


def _lean_nat_array_literal(values: Sequence[int]) -> str:
    if not values:
        raise ValueError("Expected values must contain at least one observation.")
    if any(type(v) is not int or v < 0 for v in values):
        raise ValueError("Expected values must be non-negative Nat literals.")
    values_text = ", ".join(str(v) for v in values)
    return f"#[{values_text}]"


compile_lean_check_source = build_checker_template
