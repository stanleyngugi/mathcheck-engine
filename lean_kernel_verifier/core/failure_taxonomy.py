from enum import StrEnum


class FailureTag(StrEnum):
    FORMALIZATION_ERROR = "formalization_error"
    SANITIZER_ERROR = "sanitizer_error"
    AUDIT_ERROR = "audit_error"
    SOLVER_TIMEOUT = "solver_timeout"
    SOLVER_INCOMPLETE = "solver_incomplete"
    BRANCH_ERROR = "branch_error"
    CERTIFICATE_ERROR = "certificate_error"
    LEAN_CHECK_FAIL = "lean_check_fail"
    FALLBACK_USED = "fallback_used"
    DEGENERACY_REJECTED = "degeneracy_rejected"
    CONSENSUS_FAILED = "consensus_failed"
