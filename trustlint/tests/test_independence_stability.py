import unittest

from spl_v7.causal import OnlineCausalGraphLearner
from spl_v7.schema import EvidenceArtifact


class IndependenceAndStabilityTests(unittest.TestCase):
    def test_independence_test_penalizes_duplicate_features(self) -> None:
        learner = OnlineCausalGraphLearner(independence_min_support=5, redundancy_threshold=0.85)

        for i in range(80):
            signal = 1.0 if i % 2 else 0.0
            label = bool(signal)
            learner.update(
                {
                    "tls_expiry_urgency": signal,
                    "tls_expiry_urgency_copy": signal,
                    "weak_noise": 1.0 if i % 5 == 0 else 0.0,
                },
                label,
            )

        report = learner.independence_test()
        duplicate_pairs = [
            pair
            for pair in report["pairs"]
            if {pair["left"], pair["right"]}
            == {"tls_expiry_urgency", "tls_expiry_urgency_copy"}
        ]
        self.assertEqual(len(duplicate_pairs), 1)
        self.assertFalse(duplicate_pairs[0]["independent"])
        self.assertGreaterEqual(duplicate_pairs[0]["redundancy"], 0.95)

        snapshot = learner.snapshot()
        self.assertLess(snapshot["weights"]["tls_expiry_urgency"]["independence"], 0.10)
        self.assertEqual(
            snapshot["weights"]["tls_expiry_urgency"]["redundancy_partner"],
            "tls_expiry_urgency_copy",
        )

    def test_weighted_stability_uses_label_weight(self) -> None:
        learner = OnlineCausalGraphLearner()

        for _ in range(6):
            learner.update({"stable_signal": 1.0}, True, sample_weight=5.0)
        for _ in range(6):
            learner.update({"stable_signal": 0.0}, False, sample_weight=5.0)

        snapshot = learner.snapshot()
        stats = snapshot["weights"]["stable_signal"]
        self.assertEqual(snapshot["samples_seen"], 12)
        self.assertEqual(snapshot["weighted_samples_seen"], 60.0)
        self.assertEqual(stats["weighted_support"], 60.0)
        self.assertGreater(stats["weighted_stability"], 0.65)
        self.assertTrue(all("weighted_stability" in edge for edge in snapshot["edges"]))

    def test_schema_missing_meta_preserves_defaults(self) -> None:
        artifact = EvidenceArtifact.from_dict({"data": {}, "transport_meta": {}, "integrity": {}})
        self.assertEqual(artifact.transport_meta.status, "ok")
        self.assertEqual(artifact.transport_meta.latency_ms, 0.0)
        self.assertEqual(artifact.transport_meta.bytes_received, 0)
        self.assertEqual(artifact.integrity.digest_alg, "sha256")


if __name__ == "__main__":
    unittest.main()
