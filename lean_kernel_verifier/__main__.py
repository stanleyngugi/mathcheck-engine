"""Read {specification, answer} JSON on stdin and emit a verification result."""
import argparse
from dataclasses import asdict
import json
import sys

from .specification import ProblemSpec, verify_answer
from .runner.checker_runner import CheckerRunConfig, LeanCheckerRunner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lean-bin', default='lean')
    parser.add_argument('--timeout', type=int, default=20)
    args = parser.parse_args()
    runner = LeanCheckerRunner(CheckerRunConfig(lean_executable=args.lean_bin, timeout_seconds=args.timeout))
    try:
        payload = json.load(sys.stdin)
        spec = ProblemSpec.from_dict(payload['specification'])
        result = verify_answer(spec, payload['answer'], runner)
        print(json.dumps(asdict(result)))
        return 0 if result.verified else 1
    except (ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'verified': False, 'error': str(exc)}))
        return 2
    finally:
        runner.close()


if __name__ == '__main__':
    raise SystemExit(main())
