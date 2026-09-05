import os

import pytest

from lean_kernel_verifier.certificates import PairCertificate, PairCountSpec, verify_pair_certificate
from lean_kernel_verifier.runner.checker_runner import CheckerRunConfig, LeanCheckerRunner


def test_strict_expression_bounds_and_certificate_contracts():
    for expression in ('__import__("os")', 'z == 1', 'x/y == 1', 'x'):
        with pytest.raises(ValueError):
            PairCountSpec(expression, 0, 5, 0, 5)
    with pytest.raises(ValueError):
        PairCountSpec('x < y', 0, 101, 0, 101)
    with pytest.raises(ValueError):
        PairCountSpec('x < y', False, 5, 0, 5)
    for pairs in (((0, 1), (0, 1)), ((1, 2), (0, 1)), ((True, 1),)):
        with pytest.raises(ValueError):
            PairCertificate(pairs, 2)


def test_digests_bind_constraints_and_certificate():
    assert PairCountSpec('x < y', 0, 5, 0, 5).digest != PairCountSpec('x <= y', 0, 5, 0, 5).digest
    assert PairCertificate(((0, 1),), 1).digest != PairCertificate(((0, 1),), 2).digest


@pytest.mark.skipif(not os.environ.get('LEAN_BIN'), reason='set LEAN_BIN for real certificate checks')
def test_live_completeness_not_just_witness_validity():
    spec = PairCountSpec('x < y and x+y == 4', 0, 5, 0, 5)
    runner = LeanCheckerRunner(CheckerRunConfig(lean_executable=os.environ['LEAN_BIN'], timeout_seconds=120))
    try:
        for pairs, answer, expected in (
            (((0, 4), (1, 3)), 2, True),
            (((0, 4),), 1, False),  # valid witness, incomplete set
            (((0, 4), (1, 3)), 1, False),
            (((0, 4), (2, 2)), 2, False),  # violates strict ordering
        ):
            result = verify_pair_certificate(spec, PairCertificate(pairs, answer), runner)
            assert result.verified is expected, result.checker.stdout + result.checker.stderr
            assert not result.checker.timed_out
        empty = PairCountSpec('x < y', 0, 0, 0, 5)
        assert verify_pair_certificate(empty, PairCertificate((), 0), runner).verified
    finally:
        runner.close()
