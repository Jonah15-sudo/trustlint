import unittest

from spl_v7.causal import OnlineCausalGraphLearner
from spl_v7.verification import (
    EvidenceProvenanceVerifier,
    SourceProfile,
    SourceRegistry,
    compute_artifact_hash,
)
from spl_v7.schema import EvidenceArtifact, EvidenceTransportMeta


class V71HardeningTests(unittest.TestCase):
    def test_temporal_stability_detects_drift(self) -> None:
        learner = OnlineCausalGraphLearner(stability_window=24, drift_threshold=0.20)
        for i in range(24):
            signal = 1.0 if i % 2 else 0.0
            learner.update({"drifting_signal": signal}, bool(signal), sample_weight=2.0, source_id="collector-a")
        for i in range(24):
            signal = 1.0 if i % 2 else 0.0
            learner.update({"drifting_signal": signal}, not bool(signal), sample_weight=2.0, source_id="collector-a")

        report = learner.temporal_stability_report("drifting_signal")
        self.assertEqual(report["mode"], "rolling_window_temporal_stability")
        self.assertGreater(report["drift_score"], 0.20)
        self.assertFalse(report["passed"])

    def test_conditional_independence_reduces_confounded_redundancy(self) -> None:
        learner = OnlineCausalGraphLearner(independence_min_support=10, redundancy_threshold=0.85)
        for i in range(80):
            driver = 1.0 if i % 2 else 0.0
            # These two features are correlated mostly because both follow the
            # explicit driver, but they are not byte-for-byte duplicates.
            proxy_a = driver + (0.05 if i % 5 == 0 else 0.0)
            proxy_b = driver + (0.05 if i % 7 == 0 else 0.0)
            learner.update(
                {"driver": driver, "proxy_a": proxy_a, "proxy_b": proxy_b},
                bool(driver),
                sample_weight=1.0,
                source_id="collector-a",
            )

        report = learner.independence_test()
        pair = next(p for p in report["pairs"] if {p["left"], p["right"]} == {"proxy_a", "proxy_b"})
        self.assertEqual(pair["best_conditioner"], "driver")
        self.assertLess(pair["redundancy"], pair["raw_redundancy"])

    def test_source_verification_valid_digest_raises_weight_and_report(self) -> None:
        registry = SourceRegistry([SourceProfile("collector-a", trust_weight=0.95)])
        verifier = EvidenceProvenanceVerifier(registry)
        artifact = EvidenceArtifact(
            source="collector-a",
            type="tls",
            data={"risk": 1.0, "label": True},
            transport_meta=EvidenceTransportMeta(status="ok"),
        )
        artifact.integrity.hash = compute_artifact_hash(artifact)
        report = verifier.verify(artifact)
        self.assertTrue(report["passed"])
        self.assertTrue(report["digest_valid"])
        self.assertGreater(report["score"], 0.80)

        learner = OnlineCausalGraphLearner()
        result = learner.update(
            {"risk": 1.0},
            True,
            sample_weight=2.0,
            source_id="collector-a",
            verification_report=report,
        )
        self.assertGreater(result["sample_weight"], 1.6)
        source_report = learner.source_verification_report()
        self.assertTrue(source_report["passed"])
        self.assertGreater(source_report["avg_verification_score"], 0.80)

    def test_invalid_digest_is_penalized(self) -> None:
        verifier = EvidenceProvenanceVerifier(SourceRegistry([SourceProfile("collector-a", trust_weight=0.95)]))
        artifact = EvidenceArtifact(source="collector-a", type="tls", data={"risk": 1.0})
        artifact.integrity.hash = "deadbeef"
        report = verifier.verify(artifact)
        self.assertFalse(report["passed"])
        self.assertFalse(report["digest_valid"])
        self.assertLess(report["score"], 0.75)

    def test_causal_graph_report_is_explicit(self) -> None:
        learner = OnlineCausalGraphLearner()
        for i in range(20):
            signal = 1.0 if i % 2 else 0.0
            learner.update({"signal": signal}, bool(signal), source_id="collector-a")
        report = learner.causal_graph_report()
        self.assertEqual(report["schema_version"], "spl.causal_graph.v7.1")
        self.assertIn("adjacency", report)
        self.assertIn("mechanisms", report)
        self.assertIn("signal", report["mechanisms"])
        self.assertIn("stability", report["constraints"])
        self.assertIn("source_verification", report["constraints"])


if __name__ == "__main__":
    unittest.main()
