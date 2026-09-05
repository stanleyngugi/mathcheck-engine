"""Bounded integer specifications compiled to native_decide, never raw model code.

This certifies the supplied specification, not its correspondence to prose.
Bounds are explicit and finite; no extrapolation is certified.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import hashlib
import json

from .runner.checker_runner import LeanCheckerRunner, CheckerRunResult
from .sanitizer.template import build_checker_template


def _expression(text: str, *, predicate: bool, variable: bool) -> str:
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
        if isinstance(node, ast.Name) and node.id == 'x' and variable:
            return '(Int.ofNat x)', 'int'
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
    scope: str = 'encoded_specification_only'
    trust: str = 'lean_native_compiler_and_runtime'


def verify_answer(spec: ProblemSpec, answer: int, runner: LeanCheckerRunner) -> VerificationResult:
    result = runner.run_source(compile_answer_check(spec, answer))
    return VerificationResult(spec.digest, answer, result.success, result)
