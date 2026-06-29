import unittest

from spl_v7.causal import OnlineCausalGraphLearner
from spl_v7.dsl import compile_feature_dsl
from spl_v7.kafka_pipeline import EvidencePipeline, PipelineConfig, MemoryKafkaAdapter
from spl_v7.schema import EvidenceArtifact, EvidenceTransportMeta


class PipelineTests(unittest.TestCase):
    def test_end_to_end_memory_pipeline(self) -> None:
        dsl = """
        feature tls_valid = data.valid
        feature tls_expiry_urgency = normalize(30 - data.expiry_days, 0, 30)
        feature hsts_missing = not data.headers.hsts
        feature score = clamp(0.0, 1.0, 0.5 * tls_expiry_urgency + 0.5 * hsts_missing)
        """
        program = compile_feature_dsl(dsl)
        learner = OnlineCausalGraphLearner()
        pipeline = EvidencePipeline(
            feature_program=program,
            causal_graph=learner,
            config=PipelineConfig(backend="memory"),
            adapter=MemoryKafkaAdapter(),
        )
        artifact = EvidenceArtifact(
            source="collector",
            type="tls",
            data={"valid": True, "expiry_days": 3, "headers": {"hsts": False}, "label": True},
            transport_meta=EvidenceTransportMeta(status="ok", latency_ms=10, bytes_received=123),
        )
        pipeline.ingest(artifact.to_dict())
        output = pipeline.process_one(timeout=0.05)
        self.assertIsNotNone(output)
        self.assertIn("features", output)
        self.assertIn("decision", output)
        self.assertIn("graph_snapshot", output)


if __name__ == "__main__":
    unittest.main()
