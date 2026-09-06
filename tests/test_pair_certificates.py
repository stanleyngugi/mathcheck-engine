import os

import pytest

from lean_kernel_verifier.certificates import PairCertificate, PairCountSpec, compile_pair_certificate, verify_pair_certificate
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


def test_large_certificate_uses_data_not_nested_literal_and_retains_exact_equality():
    spec = PairCountSpec('x >= 0', 0, 100, 0, 100)
    certificate = PairCertificate(tuple((x, y) for x in range(100) for y in range(100)), 10000)
    source = compile_pair_certificate(spec, certificate)
    assert 'decode_pairs "0,0;0,1;' in source
    assert 'decoded_pairs.isSome = true ∧ claimed_pairs = valid_pairs' in source
    assert 'claimed_pairs.length = 10000' in source
    assert '[(0, 0)' not in source


@pytest.mark.skipif(not os.environ.get('LEAN_BIN'), reason='set LEAN_BIN for real certificate checks')
def test_live_maximum_certificate_positive_and_incomplete_negative():
    spec = PairCountSpec('x >= 0', 0, 100, 0, 100)
    pairs = tuple((x, y) for x in range(100) for y in range(100))
    runner = LeanCheckerRunner(CheckerRunConfig(lean_executable=os.environ['LEAN_BIN'], timeout_seconds=120))
    try:
        for claimed, answer, expected in ((pairs, 10000, True), (pairs[:5000]+pairs[5001:], 9999, False),
                                           (pairs, 9999, False)):
            result = verify_pair_certificate(spec, PairCertificate(claimed, answer), runner)
            assert not result.checker.timed_out
            assert result.verified is expected, result.checker.stdout + result.checker.stderr
            if not expected:
                assert 'Tactic `native_decide` evaluated' in result.checker.stdout + result.checker.stderr
    finally:
        runner.close()


@pytest.mark.skipif(not os.environ.get('LEAN_BIN'), reason='set LEAN_BIN for real certificate checks')
def test_live_malformed_decoding_cannot_fall_back_to_empty_success():
    spec = PairCountSpec('x < y', 0, 0, 0, 1)
    source = compile_pair_certificate(spec, PairCertificate((), 0))
    runner = LeanCheckerRunner(CheckerRunConfig(lean_executable=os.environ['LEAN_BIN'], timeout_seconds=120))
    try:
        for malformed in ('1', 'x,2', '1000001,2', '1,2,3'):
            result = runner.run_source(source.replace('decode_pairs ""', f'decode_pairs "{malformed}"'))
            assert not result.success and not result.timed_out
            assert 'Tactic `native_decide` evaluated' in result.stdout + result.stderr
    finally:
        runner.close()


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
