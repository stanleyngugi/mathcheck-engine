"""Bounded integer specifications compiled to native_decide, never raw model code.

This certifies the supplied specification, not its correspondence to prose.
Bounds are explicit and finite; no extrapolation is certified.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Literal

from .runner.checker_runner import LeanCheckerRunner, CheckerRunResult
from .sanitizer.template import build_checker_template

VerificationStatus = Literal[
    'checked_success',
    'mathematical_rejection',
    'invalid_input',
    'unsupported_task',
    'operational_error',
]


# Lean 4.23's own decideNative regression test specifies this diagnostic.
# Match complete diagnostics, rather than an exit code or isolated words.
# CLI prefixes and our formatted LSP prefixes are supported. Unknown formats,
# truncated output, and additional errors deliberately remain inconclusive.
_NATIVE_FALSE_HEADER = re.compile(
    r"(?:[^\n]+:\d+:\d+:\s*error:\s*|error:\s*|\[\d+:\d+\]\s*)"
    r"Tactic `native_decide` evaluated that the proposition"
)
_LEAN_WARNING_HEADER = re.compile(r"[^\n]+:\d+:\d+:\s*warning:\s*.*")


def _native_false_diagnostics(output: str) -> bool:
    # Scan lines rather than matching nested multiline quantifiers. Long or
    # truncated pretty-printed propositions must not cause regex backtracking.
    lines = output.strip().splitlines()
    index = 0
    decisions = 0
    while index < len(lines):
        if _LEAN_WARNING_HEADER.fullmatch(lines[index]):
            index += 1
            while index < len(lines) and lines[index].startswith((' ', '\t')):
                index += 1
            while index < len(lines) and not lines[index].strip():
                index += 1
            if index < len(lines) and lines[index].startswith('Note: '):
                index += 1
                while index < len(lines) and lines[index].startswith((' ', '\t')):
                    index += 1
                while index < len(lines) and not lines[index].strip():
                    index += 1
            continue
        if not _NATIVE_FALSE_HEADER.fullmatch(lines[index]):
            return False
        index += 1
        proposition_start = index
        while index < len(lines) and lines[index].startswith((' ', '\t')):
            index += 1
        if index == proposition_start or index == len(lines) or lines[index] != 'is false':
            return False
        decisions += 1
        index += 1
        while index < len(lines) and not lines[index].strip():
            index += 1
    return decisions > 0


def checker_status(result: CheckerRunResult) -> VerificationStatus:
    """Classify trusted checker output; exit 1 alone is not a negative decision.

    This interprets diagnostics, not a separately checkable counterexample.
    A changed diagnostic format fails conservatively as an operational error.
    """
    if result.timed_out or result.backend_error or result.returncode not in (0, 1):
        return 'operational_error'
    if result.success and result.returncode == 0:
        return 'checked_success'
    output = (result.stdout + '\n' + result.stderr).strip()
    if result.returncode == 1 and _native_false_diagnostics(output):
        return 'mathematical_rejection'
    return 'operational_error'


def _expression(text: str, *, predicate: bool, variable: bool,
                variables: tuple[str, ...] = ('x',)) -> str:
    if not isinstance(text, str) or not text.strip() or len(text) > 2000:
        raise ValueError('expression must be a nonempty string of at most 2000 characters')
    try:
        tree = ast.parse(text, mode='eval')
    except (SyntaxError, RecursionError) as exc:
        raise ValueError('invalid expression') from exc
    if len(list(ast.walk(tree))) > 100:
        raise ValueError('expression is too complex')

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) is int and abs(node.value) <= 10**12:
            return f'({node.value} : Int)', 'int'
        if isinstance(node, ast.Name) and node.id in variables and variable:
            return f'(Int.ofNat {node.id})', 'int'
        if isinstance(node, ast.UnaryOp):
            value, kind = visit(node.operand)
            if isinstance(node.op, ast.USub) and kind == 'int':
                return f'(-{value})', kind
            if isinstance(node.op, ast.UAdd) and kind == 'int':
                return value, kind
            if isinstance(node.op, ast.Not) and kind == 'prop':
                return f'(Not {value})', kind
        if isinstance(node, ast.BinOp):
            left, left_kind = visit(node.left)
            right, right_kind = visit(node.right)
            if left_kind != 'int' or right_kind != 'int':
                raise ValueError('arithmetic operands must be integers')
            ops = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.FloorDiv: '/', ast.Mod: '%'}
            if isinstance(node.op, (ast.FloorDiv, ast.Mod)):
                if not isinstance(node.right, ast.Constant) or type(node.right.value) is not int or node.right.value <= 0:
                    raise ValueError('division and modulo require a positive literal divisor')
            if isinstance(node.op, ast.Pow):
                if not isinstance(node.right, ast.Constant) or type(node.right.value) is not int or not 0 <= node.right.value <= 16:
                    raise ValueError('power requires a literal exponent between 0 and 16')
                # Disallow nested powers to keep compiled computation bounded.
                if any(isinstance(n, ast.Pow) for n in ast.walk(node.left)):
                    raise ValueError('nested powers are unsupported')
                return f'({left} ^ {node.right.value})', 'int'
            if type(node.op) in ops:
                return f'({left} {ops[type(node.op)]} {right})', 'int'
        if isinstance(node, ast.Compare):
            operands = [visit(n) for n in [node.left, *node.comparators]]
            ops = {ast.Eq: '=', ast.NotEq: '≠', ast.Lt: '<', ast.LtE: '≤', ast.Gt: '>', ast.GtE: '≥'}
            if any(kind != 'int' for _, kind in operands) or any(type(op) not in ops for op in node.ops):
                raise ValueError('unsupported comparison')
            clauses = [f'({operands[i][0]} {ops[type(op)]} {operands[i+1][0]})' for i, op in enumerate(node.ops)]
            return '(' + ' ∧ '.join(clauses) + ')', 'prop'
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            values = [visit(n) for n in node.values]
            if any(kind != 'prop' for _, kind in values):
                raise ValueError('Boolean operands must be predicates')
            operator = ' ∧ ' if isinstance(node.op, ast.And) else ' ∨ '
            return '(' + operator.join(value for value, _ in values) + ')', 'prop'
        raise ValueError('only integer arithmetic, comparisons, and the bound variable x are allowed')

    result, kind = visit(tree.body)
    if kind != ('prop' if predicate else 'int'):
        raise ValueError('wrong expression type for specification')
    return result


@dataclass(frozen=True)
class ProblemSpec:
    kind: str
    expression: str
    start: int = 0
    stop: int = 0

    def __post_init__(self):
        if self.kind not in ('evaluate', 'count', 'sum', 'minimum'):
            raise ValueError('unsupported specification kind')
        if any(type(n) is not int for n in (self.start, self.stop)):
            raise ValueError('bounds must be integers')
        if not 0 <= self.start <= self.stop <= 10**6 or self.stop - self.start > 10000:
            raise ValueError('bounds must satisfy 0 <= start <= stop <= 1000000 with at most 10000 terms')
        if self.kind == 'evaluate' and (self.start or self.stop):
            raise ValueError('evaluate does not use bounds')
        if self.kind == 'minimum' and self.start == self.stop:
            raise ValueError('minimum requires a nonempty search interval')
        _expression(self.expression, predicate=self.kind in ('count', 'minimum'), variable=self.kind != 'evaluate')

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) - {'kind', 'expression', 'start', 'stop'}:
            raise ValueError('invalid specification fields')
        try:
            return cls(**data)
        except TypeError as exc:
            raise ValueError('missing specification fields') from exc

    @property
    def digest(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


def compile_answer_check(spec: ProblemSpec, answer: int) -> str:
    if type(answer) is not int or not 0 <= answer < 10**1000:
        raise ValueError('candidate must be a nonnegative integer smaller than 10**1000')
    expr = _expression(spec.expression, predicate=spec.kind in ('count', 'minimum'), variable=spec.kind != 'evaluate')
    domain = f'(List.range {spec.stop - spec.start})'
    if spec.kind == 'evaluate':
        goal = f'{expr} = Int.ofNat ans'
    elif spec.kind == 'sum':
        total = f'{domain}.foldl (fun (acc : Int) i => let x := i + {spec.start}; acc + {expr}) (0 : Int)'
        goal = f'({total}) = Int.ofNat ans'
    elif spec.kind == 'count':
        total = f'({domain}.filter (fun i => let x := i + {spec.start}; decide {expr})).length'
        goal = f'{total} = ans'
    else:
        goal = (
            f'{spec.start} ≤ ans ∧ ans < {spec.stop} ∧ '
            f'(let x := ans; {expr}) ∧ '
            f'({domain}.all (fun i => let x := i + {spec.start}; decide (x < ans → Not {expr}))) = true'
        )
    definition = (
        f'def problem_spec (ans : Nat) : Bool := decide ({goal})\n'
        f'def f (_n : Nat) : Nat := if problem_spec {answer} then 1 else 0'
    )
    return build_checker_template(definition, [1])


@dataclass
class VerificationResult:
    specification_digest: str
    answer: int
    verified: bool
    checker: CheckerRunResult
    status: VerificationStatus = 'checked_success'
    scope: str = 'encoded_specification_only'
    trust: str = 'lean_native_compiler_and_runtime'


def verify_answer(spec: ProblemSpec, answer: int, runner: LeanCheckerRunner) -> VerificationResult:
    result = runner.run_source(compile_answer_check(spec, answer))
    return VerificationResult(spec.digest, answer, result.success, result, checker_status(result))
