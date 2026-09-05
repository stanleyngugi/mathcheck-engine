"""Complete finite-relation certificates, not merely lists of satisfying witnesses."""
from dataclasses import asdict, dataclass
import hashlib
import json

from .specification import _expression, VerificationResult
from .sanitizer.template import build_checker_template


@dataclass(frozen=True)
class PairCountSpec:
    expression: str
    x_start: int
    x_stop: int
    y_start: int
    y_stop: int
    kind: str = 'count_pairs'

    def __post_init__(self):
        if self.kind != 'count_pairs':
            raise ValueError('only bounded pair counting is supported')
        for start, stop in ((self.x_start, self.x_stop), (self.y_start, self.y_stop)):
            if type(start) is not int or type(stop) is not int or not 0 <= start <= stop <= 10**6:
                raise ValueError('invalid half-open nonnegative bounds')
            if stop-start > 10000:
                raise ValueError('each axis is limited to 10000 values')
        if (self.x_stop-self.x_start)*(self.y_stop-self.y_start) > 10000:
            raise ValueError('Cartesian product exceeds 10000 pairs')
        _expression(self.expression, predicate=True, variable=True, variables=('x', 'y'))

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) - set(cls.__dataclass_fields__):
            raise ValueError('invalid pair specification fields')
        try:
            return cls(**data)
        except TypeError as exc:
            raise ValueError('missing pair specification fields') from exc

    @property
    def digest(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class PairCertificate:
    pairs: tuple[tuple[int, int], ...]
    answer: int

    def __post_init__(self):
        if type(self.answer) is not int or not 0 <= self.answer <= 10000:
            raise ValueError('answer must be an integer from 0 to 10000')
        if not isinstance(self.pairs, tuple) or len(self.pairs) > 10000:
            raise ValueError('certificate requires at most 10000 immutable pairs')
        for pair in self.pairs:
            if (not isinstance(pair, tuple) or len(pair) != 2
                    or any(type(n) is not int or not 0 <= n <= 10**6 for n in pair)):
                raise ValueError('invalid certificate pair')
        if tuple(sorted(set(self.pairs))) != self.pairs:
            raise ValueError('pairs must be unique and lexicographically sorted')

    @property
    def digest(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


def compile_pair_certificate(spec: PairCountSpec, certificate: PairCertificate) -> str:
    expression = _expression(spec.expression, predicate=True, variable=True, variables=('x', 'y'))
    pairs = ', '.join(f'({x}, {y})' for x, y in certificate.pairs)
    definition = (
        'def valid_pairs : List (Nat × Nat) :=\n'
        f'  let domain := (List.range {spec.x_stop-spec.x_start}).flatMap (fun i =>\n'
        f'    (List.range {spec.y_stop-spec.y_start}).map (fun j => (i + {spec.x_start}, j + {spec.y_start})))\n'
        f'  domain.filter (fun p => let x := p.1; let y := p.2; decide {expression})\n'
        f'def claimed_pairs : List (Nat × Nat) := [{pairs}]\n'
        'def f (_n : Nat) : Nat :=\n'
        f'  if decide (claimed_pairs = valid_pairs ∧ claimed_pairs.length = {certificate.answer}) then 1 else 0'
    )
    return build_checker_template(definition, [1])


@dataclass
class PairVerificationResult(VerificationResult):
    certificate_digest: str = ''


def verify_pair_certificate(spec: PairCountSpec, certificate: PairCertificate, runner) -> PairVerificationResult:
    result = runner.run_source(compile_pair_certificate(spec, certificate))
    return PairVerificationResult(
        spec.digest, certificate.answer, result.success, result,
        scope='encoded_bounded_pair_count_with_complete_enumeration',
        certificate_digest=certificate.digest,
    )
