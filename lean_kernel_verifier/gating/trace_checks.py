from __future__ import annotations

import re
from typing import Iterable

from ..core.types import TraceChecksResult

BOUNDARY_PATTERNS = (
    re.compile(r"\b(?:a|f)\(\s*(\d+)\s*\)\s*=\s*(-?\d+)", re.IGNORECASE),
    re.compile(r"\b(?:a|f)_\{?(\d+)\}?\s*=\s*(-?\d+)", re.IGNORECASE),
)

DIVISIBILITY_PATTERNS = (
    re.compile(r"\bdivisible by\s+(\d+)\b", re.IGNORECASE),
    re.compile(r"\bmultiple of\s+(\d+)\b", re.IGNORECASE),
)

COUNTING_KEYWORDS = (
    "count",
    "number of",
    "how many",
    "ways",
    "arrangements",
    "arrangement",
)


def extract_boundary_conditions(problem_text: str) -> dict[int, int]:
    boundaries: dict[int, int] = {}
    for pattern in BOUNDARY_PATTERNS:
        for match in pattern.finditer(problem_text):
            index = int(match.group(1))
            value = int(match.group(2))
            boundaries[index] = value
    return boundaries


def infer_monotonicity_requirement(problem_text: str) -> str | None:
    text = problem_text.lower()
    if "strictly increasing" in text:
        return "strictly_increasing"
    if "nondecreasing" in text or "non-decreasing" in text:
        return "nondecreasing"
    if "strictly decreasing" in text:
        return "strictly_decreasing"
    if "nonincreasing" in text or "non-increasing" in text:
        return "nonincreasing"
    if "increasing" in text:
        return "strictly_increasing"
    if "decreasing" in text:
        return "strictly_decreasing"
    return None


def extract_divisibility_constraints(problem_text: str) -> list[int]:
    divisors: set[int] = set()
    for pattern in DIVISIBILITY_PATTERNS:
        for match in pattern.finditer(problem_text):
            divisor = int(match.group(1))
            if divisor > 1:
                divisors.add(divisor)
    return sorted(divisors)


def run_trace_vs_problem_checks(
    problem_text: str,
    trace: Iterable[int],
    *,
    extra_boundaries: dict[int, int] | None = None,
    extra_divisibility: Iterable[int] | None = None,
) -> TraceChecksResult:
    values = list(trace)
    findings: list[str] = []
    applied_checks: list[str] = []

    boundaries = extract_boundary_conditions(problem_text)
    if extra_boundaries:
        boundaries.update(extra_boundaries)
    boundary_passed = True
    if boundaries:
        applied_checks.append("boundary")
        for index, expected in sorted(boundaries.items()):
            if index >= len(values):
                findings.append(f"Boundary check unresolved: index {index} is outside trace range.")
                boundary_passed = False
                continue
            if values[index] != expected:
                findings.append(
                    f"Boundary mismatch at index {index}: expected {expected}, observed {values[index]}."
                )
                boundary_passed = False

    monotonicity = infer_monotonicity_requirement(problem_text)
    monotonicity_passed = True
    if monotonicity is not None and len(values) >= 2:
        applied_checks.append("monotonicity")
        if monotonicity == "strictly_increasing":
            monotonicity_passed = all(values[i + 1] > values[i] for i in range(len(values) - 1))
        elif monotonicity == "nondecreasing":
            monotonicity_passed = all(values[i + 1] >= values[i] for i in range(len(values) - 1))
        elif monotonicity == "strictly_decreasing":
            monotonicity_passed = all(values[i + 1] < values[i] for i in range(len(values) - 1))
        elif monotonicity == "nonincreasing":
            monotonicity_passed = all(values[i + 1] <= values[i] for i in range(len(values) - 1))
        if not monotonicity_passed:
            findings.append(f"Monotonicity check failed for requirement `{monotonicity}`.")

    divisibility = extract_divisibility_constraints(problem_text)
    if extra_divisibility is not None:
        divisibility.extend(int(value) for value in extra_divisibility if int(value) > 1)
    divisibility = sorted(set(divisibility))

    divisibility_passed = True
    if divisibility:
        applied_checks.append("divisibility")
        for divisor in divisibility:
            if any(value % divisor != 0 for value in values):
                findings.append(f"Divisibility check failed for divisor {divisor}.")
                divisibility_passed = False

    counting_passed = True
    lower_text = problem_text.lower()
    if any(keyword in lower_text for keyword in COUNTING_KEYWORDS):
        applied_checks.append("counting_nonnegative")
        if any(value < 0 for value in values):
            findings.append("Counting check failed: negative values in trace.")
            counting_passed = False

    inconclusive = not applied_checks
    passed = (
        not inconclusive
        and boundary_passed
        and monotonicity_passed
        and divisibility_passed
        and counting_passed
    )
    return TraceChecksResult(
        passed=passed,
        inconclusive=inconclusive,
        boundary_passed=boundary_passed,
        monotonicity_passed=monotonicity_passed,
        divisibility_passed=divisibility_passed,
        applied_checks=applied_checks,
        findings=findings,
    )
