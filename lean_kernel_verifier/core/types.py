from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Tier = Literal["Tier A", "Tier B", "Tier C"]
FormulaKind = Literal[
    "polynomial",
    "bm_recurrence",
    "holonomic_lite",
    "case_split",
    "modular_cycle",
    "structural",
    "oeis",
    "multiplicative",
]


@dataclass(slots=True)
class TraceSample:
    source_id: str
    values: tuple[int, ...]
    strategy: str = "unknown"
    interpretation: str = "default"


@dataclass(slots=True)
class TraceConsensusResult:
    accepted: bool
    consensus_trace: tuple[int, ...] | None
    cluster_size: int
    total_traces: int
    cluster_count: int
    min_required: int
    warnings: list[str] = field(default_factory=list)
    alternative_clusters: list[tuple[int, tuple[int, ...]]] = field(default_factory=list)


@dataclass(slots=True)
class FormulaCandidate:
    kind: FormulaKind
    lean_definition: str
    holdout_passed: bool
    adversarial_passed: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TraceChecksResult:
    passed: bool
    inconclusive: bool
    boundary_passed: bool
    monotonicity_passed: bool
    divisibility_passed: bool
    applied_checks: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class VerifierRunResult:
    accepted: bool
    tier: Tier
    answer: int | None
    reason: str
    consensus: TraceConsensusResult
    trace_checks: TraceChecksResult
    candidate: FormulaCandidate | None
    checker_success: bool
    checker_stderr: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def public_view(self) -> dict[str, Any]:
        """Stable JSON-ready view of the fields external callers may rely on."""
        return {
            "accepted": self.accepted,
            "tier": self.tier,
            "answer": self.answer,
            "reason": self.reason,
            "checker_success": self.checker_success,
            "candidate_kind": self.candidate.kind if self.candidate else None,
            "consensus": {
                "cluster_size": self.consensus.cluster_size,
                "total_traces": self.consensus.total_traces,
                "minimum_required": self.consensus.min_required,
            },
            "trace_checks": {
                "applied": list(self.trace_checks.applied_checks),
                "findings": list(self.trace_checks.findings),
            },
        }
