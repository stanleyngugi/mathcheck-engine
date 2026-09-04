"""Gröbner-based geometric statement verifier (Wu-style algebraization).

Encodes a geometric configuration as polynomial hypotheses over assigned
coordinates and checks whether the conclusion polynomial belongs to the
hypothesis ideal via Groebner-basis reduction.
"""

from __future__ import annotations

from typing import Any


def _load_sympy():
    try:
        import sympy as sp

        return sp
    except ImportError:
        return None


def verify_geometry_statement(
    hypotheses: list[tuple[str, str]],
    conclusion: str,
    variables: list[str],
) -> dict[str, Any]:
    """Check `conclusion == 0` follows from `hypotheses` equalities.

    hypotheses: list of (lhs, rhs) string pairs parsed as LaTeX-free sympy
    expressions (`^` allowed for powers). conclusion: expression claimed to
    vanish. variables: ordered variable names.

    Returns {proved, reason, remainder, leading_conditions}.
    """
    result: dict[str, Any] = {
        "proved": False,
        "reason": "",
        "remainder": None,
        "leading_conditions": [],
    }
    sp = _load_sympy()
    if sp is None:
        result["reason"] = "sympy unavailable"
        return result
    if len(variables) > 8:
        result["reason"] = "too many variables"
        return result
    syms = [sp.Symbol(name) for name in variables]
    locals_map = {name: sym for name, sym in zip(variables, syms)}

    def parse(text: str):
        return sp.sympify(str(text).replace("^", "**"), locals=locals_map)

    hypothesis_polys = []
    try:
        for lhs, rhs in hypotheses:
            expr = sp.expand(parse(lhs) - parse(rhs))
            poly = sp.Poly(expr, *syms)
            hypothesis_polys.append(poly.as_expr())
        conclusion_expr = sp.expand(parse(conclusion))
        sp.Poly(conclusion_expr, *syms)
    except Exception as exc:  # noqa: BLE001
        result["reason"] = f"parse/poly failure: {type(exc).__name__}"
        return result
    if not hypothesis_polys:
        result["reason"] = "no hypotheses"
        return result

    try:
        basis = sp.groebner(hypothesis_polys, *syms, order="lex")
    except Exception as exc:  # noqa: BLE001
        result["reason"] = f"groebner failure: {type(exc).__name__}"
        return result

    try:
        quotient, remainder = basis.reduce(conclusion_expr)
    except Exception as exc:  # noqa: BLE001
        result["reason"] = (
            f"reduction failure ({type(exc).__name__}): multiply out any "
            "denominators so the conclusion is a polynomial"
        )
        return result

    remainder_expanded = sp.expand(remainder)
    proved = remainder_expanded == 0
    leading_conditions = [
        str(sp.Poly(p.as_expr(), *syms).LC()) for p in basis.polys if p.LC() != 1
    ]
    result["proved"] = bool(proved)
    result["reason"] = (
        "conclusion polynomial reduces to zero modulo the Groebner basis"
        if proved
        else "conclusion does not follow from hypotheses"
    )
    result["remainder"] = str(remainder_expanded)
    result["leading_conditions"] = sorted(set(leading_conditions))
    return result


def certify_geometry_statement(
    hypotheses: list[tuple[str, str]],
    conclusion: str,
    variables: list[str],
    witness: dict[str, int | float],
) -> dict[str, Any]:
    """verify_geometry_statement plus a rational witness sanity check.

    A witness is one concrete assignment satisfying all hypotheses AND the
    conclusion numerically.
    """
    result = verify_geometry_statement(hypotheses, conclusion, variables)
    witness_checks = _check_witness(hypotheses, conclusion, variables, witness)
    result["witness"] = {
        "values": witness,
        "satisfies_hypotheses": witness_checks["hypotheses"],
        "satisfies_conclusion": witness_checks["conclusion"],
    }
    if result["proved"] and not (
        witness_checks["hypotheses"] and witness_checks["conclusion"]
    ):
        result["proved"] = False
        result["reason"] = "witness check contradicts symbolic reduction"
    return result


def _check_witness(
    hypotheses: list[tuple[str, str]],
    conclusion: str,
    variables: list[str],
    witness: dict[str, int | float],
) -> dict[str, bool]:
    sp = _load_sympy()
    if sp is None:
        return {"hypotheses": False, "conclusion": False}
    syms = {name: sp.Symbol(name) for name in variables}
    substitution = {}
    for name, value in witness.items():
        if name in syms:
            substitution[syms[name]] = sp.Rational(str(value))
    ok_hypotheses = True
    for lhs, rhs in hypotheses:
        lhs_value = sp.nsimplify(
            sp.N(parse_safe(lhs, syms).subs(substitution), 30), rational=True
        )
        rhs_value = sp.nsimplify(
            sp.N(parse_safe(rhs, syms).subs(substitution), 30), rational=True
        )
        if lhs_value != rhs_value:
            ok_hypotheses = False
            break
    conclusion_value = sp.nsimplify(
        sp.N(parse_safe(conclusion, syms).subs(substitution), 30), rational=True
    )
    return {"hypotheses": ok_hypotheses, "conclusion": conclusion_value == 0}


def parse_safe(text: str, symbol_map: dict[str, object]):
    sp = _load_sympy()
    return sp.sympify(str(text).replace("^", "**"), locals=symbol_map)
