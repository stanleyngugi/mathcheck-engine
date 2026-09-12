"""Minimal MathCheck Engine example with one acceptance and one rejection."""
from __future__ import annotations

import argparse
import json

from lean_kernel_verifier.runner.checker_runner import CheckerRunConfig, LeanCheckerRunner
from lean_kernel_verifier.specification import ProblemSpec, verify_answer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lean-bin", default="lean")
    args = parser.parse_args()

    specification = ProblemSpec("count", "x%3 == 0", 1, 100)
    runner = LeanCheckerRunner(CheckerRunConfig(lean_executable=args.lean_bin))
    try:
        accepted = verify_answer(specification, 33, runner)
        rejected = verify_answer(specification, 32, runner)
    finally:
        runner.close()

    print(json.dumps({
        "project": "MathCheck Engine",
        "scope": accepted.scope,
        "specification_digest": accepted.specification_digest,
        "candidate_33": accepted.status,
        "candidate_32": rejected.status,
    }, indent=2))
    return 0 if accepted.verified and rejected.status == "mathematical_rejection" else 1


if __name__ == "__main__":
    raise SystemExit(main())
