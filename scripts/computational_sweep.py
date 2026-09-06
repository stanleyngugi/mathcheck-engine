"""Fixed native-computation size sweep; no model calls or prose claims."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time

from lean_kernel_verifier.specification import ProblemSpec, verify_answer
from lean_kernel_verifier.certificates import PairCountSpec, PairCertificate, verify_pair_certificate
from lean_kernel_verifier.runner.checker_runner import CheckerRunConfig, LeanCheckerRunner


def run(lean_bin, output):
    rows = []
    # Each trial starts a fresh runner. Repeat means repeat measurement, not a
    # persistent compiler cache or independently controlled OS cold cache.
    with output.open('x') as stream:
        for size in (10, 100, 1000, 10000):
            for kind in ('sum', 'count', 'pairs'):
                for repeat in range(2):
                    runner = LeanCheckerRunner(CheckerRunConfig(lean_executable=lean_bin, timeout_seconds=120))
                    try:
                        if kind == 'pairs':
                            spec = PairCountSpec('x<y', 0, 1, 0, size)
                            pairs = tuple((0, y) for y in range(1, size))
                            candidates = [(True, PairCertificate(pairs, len(pairs))),
                                          (False, PairCertificate(pairs[:-1], len(pairs)-1))]
                        else:
                            spec = ProblemSpec(kind, 'x*x' if kind == 'sum' else 'x%7==0', 0, size)
                            answer = (size-1)*size*(2*size-1)//6 if kind == 'sum' else (size-1)//7+1
                            candidates = [(True, answer), (False, answer+1)]
                        for expected, candidate in candidates:
                            started = time.monotonic()
                            result = (verify_pair_certificate(spec, candidate, runner) if kind == 'pairs'
                                      else verify_answer(spec, candidate, runner))
                            checker = result.checker
                            diagnostic = checker.stdout + checker.stderr
                            false_marker = 'Tactic `native_decide` evaluated' in diagnostic and 'is false' in diagnostic
                            operational = bool(checker.timed_out or checker.backend_error or
                                               (not result.verified and not false_marker))
                            row = dict(size=size, kind=kind, repeat=repeat, expected=expected,
                                       verified=result.verified, seconds=time.monotonic()-started,
                                       operational_failure=operational, mathematical_rejection=false_marker,
                                       passed=(result.verified is expected and not operational),
                                       specification_digest=spec.digest)
                            stream.write(json.dumps(row)+'\n')
                            stream.flush()
                            rows.append(row)
                    finally:
                        runner.close()
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--lean-bin', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = run(args.lean_bin, args.output)
    print(json.dumps({'checks': len(rows), 'passed': sum(row['passed'] for row in rows),
                      'operational_failures': sum(row['operational_failure'] for row in rows)}))
    raise SystemExit(0 if all(row['passed'] for row in rows) else 1)
