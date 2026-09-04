from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from ..core.types import TraceConsensusResult, TraceSample


def cluster_traces(
    traces: Iterable[TraceSample], prefix_terms: int = 20
) -> dict[tuple[int, ...], list[TraceSample]]:
    buckets: dict[tuple[int, ...], list[TraceSample]] = defaultdict(list)
    for trace in traces:
        key = _cluster_key(trace.values, prefix_terms)
        buckets[key].append(trace)
    return dict(buckets)


def select_consensus_trace(
    traces: Iterable[TraceSample],
    *,
    min_cluster_size: int,
    expected_k: int = 16,
    prefix_terms: int = 20,
) -> TraceConsensusResult:
    trace_list = list(traces)
    warnings: list[str] = []

    if not trace_list:
        return TraceConsensusResult(
            accepted=False,
            consensus_trace=None,
            cluster_size=0,
            total_traces=0,
            cluster_count=0,
            min_required=min_cluster_size,
            warnings=["No traces were provided."],
        )

    if len(trace_list) < expected_k:
        warnings.append(
            f"Expected K={expected_k} traces but received K={len(trace_list)}."
        )

    clusters = cluster_traces(trace_list, prefix_terms=prefix_terms)
    ranked = sorted(
        clusters.values(),
        key=lambda cluster: (-len(cluster), cluster[0].source_id),
    )
    best = ranked[0]
    consensus_trace = _common_prefix([item.values for item in best])
    if not consensus_trace:
        warnings.append("Largest cluster has no common prefix.")

    accepted = len(best) >= min_cluster_size and bool(consensus_trace)
    if not accepted:
        warnings.append(
            "Consensus threshold not met: "
            f"largest cluster={len(best)}, required={min_cluster_size}."
        )

    alt_clusters: list[tuple[int, tuple[int, ...]]] = []
    for cluster in ranked[1:]:
        alt_clusters.append((len(cluster), _common_prefix([item.values for item in cluster])[:8]))

    return TraceConsensusResult(
        accepted=accepted,
        consensus_trace=consensus_trace if consensus_trace else None,
        cluster_size=len(best),
        total_traces=len(trace_list),
        cluster_count=len(clusters),
        min_required=min_cluster_size,
        warnings=warnings,
        alternative_clusters=alt_clusters,
    )


def extract_common_prefix(
    traces: Iterable[TraceSample | tuple[int, ...]],
) -> tuple[int, ...]:
    seqs: list[tuple[int, ...]] = []
    for item in traces:
        if isinstance(item, TraceSample):
            seqs.append(item.values)
        else:
            seqs.append(item)
    return _common_prefix(seqs)


def _cluster_key(values: tuple[int, ...], prefix_terms: int) -> tuple[int, ...]:
    if prefix_terms <= 0:
        return values
    return values[:prefix_terms]


def _common_prefix(traces: list[tuple[int, ...]]) -> tuple[int, ...]:
    if not traces:
        return ()
    min_len = min(len(trace) for trace in traces)
    out: list[int] = []
    for idx in range(min_len):
        value = traces[0][idx]
        if any(trace[idx] != value for trace in traces[1:]):
            break
        out.append(value)
    return tuple(out)
