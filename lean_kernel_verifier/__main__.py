"""Read {specification, answer} JSON on stdin and emit a verification result."""
import argparse
from dataclasses import asdict
import json
import sys

from .specification import ProblemSpec, verify_answer
from .certificates import PairCountSpec, PairCertificate, verify_pair_certificate
from .runner.checker_runner import CheckerRunConfig, LeanCheckerRunner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lean-bin', default='lean')
    parser.add_argument('--timeout', type=int, default=20)
    args = parser.parse_args()
    runner = LeanCheckerRunner(CheckerRunConfig(lean_executable=args.lean_bin, timeout_seconds=args.timeout))
    try:
        raw = sys.stdin.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('request exceeds 2 MB character limit')
        payload = json.loads(raw)
        if not isinstance(payload, dict) or not isinstance(payload.get('specification'), dict):
            raise ValueError('request requires a specification object')
        if payload['specification'].get('kind') == 'count_pairs':
            if set(payload) != {'specification', 'answer', 'pairs'} or not isinstance(payload['pairs'], list) or len(payload['pairs']) > 10000:
                raise ValueError('pair checking requires specification, answer, and at most 10000 pairs')
            spec = PairCountSpec.from_dict(payload['specification'])
            certificate = PairCertificate(tuple(tuple(pair) for pair in payload['pairs']), payload['answer'])
            result = verify_pair_certificate(spec, certificate, runner)
        else:
            if set(payload) != {'specification', 'answer'}:
                raise ValueError('request requires exactly specification and answer')
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
