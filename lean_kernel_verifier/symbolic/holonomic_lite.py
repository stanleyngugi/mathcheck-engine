from __future__ import annotations

from textwrap import dedent
from typing import Iterable, Sequence

from ..core.types import FormulaCandidate


def find_holonomic_lite_candidate(
    trace: Sequence[int],
    *,
    holdout_terms: int = 4,
    adversarial_indices: Iterable[int] | None = None,
    parameter_bound: int = 12,
) -> FormulaCandidate | None:
    if len(trace) < 8:
        return None
    if any(value < 0 for value in trace):
        return None

    holdout_terms = max(0, min(holdout_terms, len(trace) - 3))
    train_end = len(trace) - holdout_terms
    train = list(trace[:train_end])
    if len(train) < 4:
        return None

    best: tuple[int, int, int, int] | None = None
    for w in range(max(0, parameter_bound) + 1):
        for z in range(max(0, parameter_bound) + 1):
            if w == 0 and z == 0:
                continue
            samples: list[tuple[int, int]] = []
            valid = True
            for n in range(len(train) - 1):
                den = (w * n) + z
                if den == 0:
                    valid = False
                    break
                a_n = train[n]
                a_next = train[n + 1]
                scaled = a_next * den
                if a_n == 0:
                    if scaled != 0:
                        valid = False
                        break
                    continue
                if scaled % a_n != 0:
                    valid = False
                    break
                samples.append((n, scaled // a_n))
            if not valid or not samples:
                continue

            uv = _fit_linear_samples(samples, parameter_bound=max(0, parameter_bound))
            if uv is None:
                continue
            u, v = uv
            params = (u, v, w, z)
            if _recurrence_matches(trace, params, train_end=train_end):
                best = params
                break
        if best is not None:
            break

    if best is None:
        return None

    u, v, w, z = best
    holdout_idx = list(range(train_end, len(trace)))
    holdout_passed = all(
        evaluate_holonomic_lite(trace[0], u, v, w, z, idx) == trace[idx] for idx in holdout_idx
    )
    adv_idx = _normalize_indices(adversarial_indices, len(trace))
    adversarial_passed = all(
        evaluate_holonomic_lite(trace[0], u, v, w, z, idx) == trace[idx] for idx in adv_idx
    )

    return FormulaCandidate(
        kind="holonomic_lite",
        lean_definition=build_holonomic_lite_lean_definition(
            seed=trace[0], u=u, v=v, w=w, z=z
        ),
        holdout_passed=holdout_passed,
        adversarial_passed=adversarial_passed,
        metadata={
            "seed": trace[0],
            "u": u,
            "v": v,
            "w": w,
            "z": z,
            "holdout_indices": holdout_idx,
            "adversarial_indices": adv_idx,
        },
    )


def evaluate_holonomic_lite(seed: int, u: int, v: int, w: int, z: int, n: int) -> int | None:
    if n < 0:
        return None
    if min(seed, u, v, w, z) < 0:
        return None
    value = int(seed)
    for i in range(n):
        den = (w * i) + z
        if den == 0:
            return None
        num = ((u * i) + v) * value
        if num % den != 0:
            return None
        value = num // den
    return value


def build_holonomic_lite_lean_definition(
    *,
    seed: int,
    u: int,
    v: int,
    w: int,
    z: int,
) -> str:
    if min(seed, u, v, w, z) < 0:
        raise ValueError("Holonomic-lite parameters must be Nat-compatible.")
    return dedent(
        f"""
        def f (n : Nat) : Nat :=
          let seed : Nat := {seed}
          let rec build (i : Nat) (acc : Nat) (fuel : Nat) : Nat :=
            match fuel with
            | 0 => acc
            | fuel' + 1 =>
                if i == n then
                  acc
                else
                  let den : Nat := ({w} * i) + {z}
                  let num : Nat := (({u} * i) + {v}) * acc
                  let next : Nat := if den == 0 then 0 else num / den
                  build (i + 1) next fuel'
          build 0 seed (n + 1)
        """
    ).strip()


def _fit_linear_samples(
    samples: Sequence[tuple[int, int]],
    *,
    parameter_bound: int,
) -> tuple[int, int] | None:
    if not samples:
        return None
    if len(samples) == 1:
        _, r = samples[0]
        if 0 <= r <= parameter_bound:
            return (0, r)
        return None

    for i in range(len(samples)):
        n1, r1 = samples[i]
        for j in range(i + 1, len(samples)):
            n2, r2 = samples[j]
            delta_n = n2 - n1
            delta_r = r2 - r1
            if delta_n == 0 or delta_r % delta_n != 0:
                continue
            u = delta_r // delta_n
            v = r1 - (u * n1)
            if u < 0 or v < 0 or u > parameter_bound or v > parameter_bound:
                continue
            if all(((u * n) + v) == r for n, r in samples):
                return (u, v)
    return None


def _recurrence_matches(
    trace: Sequence[int],
    params: tuple[int, int, int, int],
    *,
    train_end: int,
) -> bool:
    u, v, w, z = params
    for idx in range(train_end):
        predicted = evaluate_holonomic_lite(trace[0], u, v, w, z, idx)
        if predicted is None or predicted != trace[idx]:
            return False
    return True


def _normalize_indices(indices: Iterable[int] | None, length: int) -> list[int]:
    if indices is None:
        return []
    return sorted({idx for idx in indices if 0 <= idx < length})
