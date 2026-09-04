import unittest

from lean_kernel_verifier.consensus.trace_consensus import (
    cluster_traces,
    extract_common_prefix,
    select_consensus_trace,
)
from lean_kernel_verifier.core.types import TraceSample


class TraceConsensusTests(unittest.TestCase):
    def test_accepts_consensus_cluster(self) -> None:
        majority = tuple(2 * n for n in range(25))
        traces = [
            TraceSample(source_id=f"m{i}", values=majority, strategy="dp")
            for i in range(12)
        ]
        traces.extend(
            TraceSample(
                source_id=f"n{i}",
                values=tuple((2 * n) + 1 for n in range(25)),
                strategy="enum",
            )
            for i in range(4)
        )

        result = select_consensus_trace(
            traces, min_cluster_size=10, expected_k=16, prefix_terms=20
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.cluster_size, 12)
        self.assertEqual(result.consensus_trace, majority)
        self.assertEqual(result.cluster_count, 2)

    def test_rejects_when_cluster_below_threshold(self) -> None:
        even_trace = tuple(2 * n for n in range(20))
        odd_trace = tuple((2 * n) + 1 for n in range(20))
        traces = [
            TraceSample(source_id=f"e{i}", values=even_trace)
            for i in range(9)
        ] + [
            TraceSample(source_id=f"o{i}", values=odd_trace)
            for i in range(7)
        ]

        result = select_consensus_trace(
            traces, min_cluster_size=10, expected_k=16, prefix_terms=20
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.cluster_size, 9)
        self.assertIn("Consensus threshold not met", " ".join(result.warnings))

    def test_extract_common_prefix(self) -> None:
        traces = [
            TraceSample(source_id="1", values=(1, 2, 3, 4, 5)),
            TraceSample(source_id="2", values=(1, 2, 3, 9, 10)),
            TraceSample(source_id="3", values=(1, 2, 3, 4, 8)),
        ]
        prefix = extract_common_prefix(traces)
        self.assertEqual(prefix, (1, 2, 3))

    def test_cluster_traces(self) -> None:
        t1 = TraceSample(source_id="1", values=(1, 2, 3, 4))
        t2 = TraceSample(source_id="2", values=(1, 2, 3, 5))
        t3 = TraceSample(source_id="3", values=(2, 4, 6, 8))
        clusters = cluster_traces([t1, t2, t3], prefix_terms=3)
        self.assertEqual(len(clusters), 2)
        self.assertEqual(len(clusters[(1, 2, 3)]), 2)
        self.assertEqual(len(clusters[(2, 4, 6)]), 1)


if __name__ == "__main__":
    unittest.main()
