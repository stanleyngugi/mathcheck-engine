"""Seeded, parameter-varying computational checks, independent of prose fixtures."""
import os
import random

import pytest

from lean_kernel_verifier.certificates import PairCertificate, PairCountSpec, verify_pair_certificate
from lean_kernel_verifier.runner.checker_runner import CheckerRunConfig, LeanCheckerRunner
from lean_kernel_verifier.specification import ProblemSpec, verify_answer


@pytest.mark.skipif(not os.environ.get('LEAN_BIN'), reason='set LEAN_BIN for generated live checks')
def test_generated_signed_arithmetic_bounds_and_wrong_answers():
    rng = random.Random(20260905)
    runner = LeanCheckerRunner(CheckerRunConfig(lean_executable=os.environ['LEAN_BIN'], timeout_seconds=120))
    try:
        for _ in range(4):
            start = rng.randrange(0, 6)
            stop = start+rng.randrange(5, 16)
            divisor = rng.randrange(2, 9)
            shift = rng.randrange(1, 20)
            threshold = rng.randrange(start, stop)
            cases = [
                (ProblemSpec('evaluate', f'100 + (-{shift})//{divisor} + (-{shift})%{divisor}'),
                 100+(-shift)//divisor+(-shift)%divisor),
                (ProblemSpec('sum', f'100 + (x-{shift})//{divisor}', start, stop),
                 sum(100+(x-shift)//divisor for x in range(start, stop))),
                (ProblemSpec('count', f'not (x%{divisor} == 0) and x != {threshold}', start, stop),
                 sum(x % divisor != 0 and x != threshold for x in range(start, stop))),
                (ProblemSpec('minimum', f'x >= {threshold}', start, stop), threshold),
            ]
            for spec, answer in cases:
                for candidate, expected in ((answer, True), (answer+1, False)):
                    result = verify_answer(spec, candidate, runner)
                    assert not result.checker.timed_out
                    assert result.verified is expected, (spec, candidate, result.checker)
    finally:
        runner.close()


@pytest.mark.skipif(not os.environ.get('LEAN_BIN'), reason='set LEAN_BIN for generated live checks')
def test_generated_pairs_reject_omission_and_wrong_cardinality():
    rng = random.Random(9052026)
    runner = LeanCheckerRunner(CheckerRunConfig(lean_executable=os.environ['LEAN_BIN'], timeout_seconds=120))
    try:
        for _ in range(8):
            start, width = rng.randrange(0, 5), rng.randrange(4, 9)
            stop, divisor = start+width, rng.randrange(2, 5)
            spec = PairCountSpec(f'x < y and (x-y)%{divisor} != 0', start, stop, start, stop)
            pairs = tuple((x, y) for x in range(start, stop) for y in range(start, stop)
                          if x < y and (x-y) % divisor != 0)
            assert pairs
            for certificate, expected in ((PairCertificate(pairs, len(pairs)), True),
                                          (PairCertificate(pairs[:-1], len(pairs)-1), False),
                                          (PairCertificate(pairs, len(pairs)+1), False)):
                result = verify_pair_certificate(spec, certificate, runner)
                assert not result.checker.timed_out
                assert result.verified is expected, (spec, certificate, result.checker)
    finally:
        runner.close()
