import unittest

from spl_v7.causal import OnlineCausalGraphLearner
from spl_v7.dsl import compile_feature_dsl
from spl_v7.kafka_pipeline import EvidencePipeline, PipelineConfig, MemoryKafkaAdapter
from spl_v7.schema import EvidenceArtifact


class CrossSourceAndInterventionTests(unittest.TestCase):
    def test_cross_source_corroboration_penalizes_single_source(self) -> None:
        one_source = OnlineCausalGraphLearner(source_min_support=2.0, min_corroborating_sources=2)
        for i in range(40):
            signal = 1.0 if i % 2 else 0.0
            one_source.update({"transport_risk": signal}, bool(signal), source_id="collector-a")

        single = one_source.cross_source_corroboration("transport_risk")
        self.assertEqual(single["distinct_sources"], 1)
        self.assertFalse(single["passed"])
        self.assertLess(single["score"], 0.50)

    def test_cross_source_corroboration_passes_when_independent_sources_agree(self) -> None:
        learner = OnlineCausalGraphLearner(source_min_support=2.0, min_corroborating_sources=2)
        for source in ["collector-a", "collector-b", "collector-c"]:
            for i in range(40):
                signal = 1.0 if i % 2 else 0.0
                learner.update({"transport_risk": signal}, bool(signal), source_id=source)

        report = learner.cross_source_corroboration("transport_risk")
        self.assertEqual(report["distinct_sources"], 3)
        self.assertTrue(report["passed"])
        self.assertGreater(report["score"], 0.85)

        edge = learner.edges()[0].to_dict()
        self.assertIn("cross_source_corroboration", edge)
        self.assertGreater(edge["cross_source_corroboration"], 0.85)

    def test_intervention_approximation_reports_probability_shift(self) -> None:
        learner = OnlineCausalGraphLearner(source_min_support=2.0, min_corroborating_sources=2)
        for source in ["collector-a", "collector-b"]:
            for i in range(80):
                signal = 1.0 if i % 2 else 0.0
                learner.update({"transport_risk": signal, "noise": 0.5}, bool(signal), source_id=source)

        effect = learner.intervention_effect("transport_risk")
        self.assertEqual(effect["direction"], "positive")
        self.assertGreater(effect["abs_effect"], 0.20)

        snapshot = learner.snapshot()
        self.assertIn("intervention_approximation", snapshot)
        self.assertTrue(any(edge["intervention_effect"] > 0.20 for edge in snapshot["edges"]))

    def test_pipeline_passes_source_to_corroboration_gate(self) -> None:
        dsl = """
        feature transport_risk = data.risk
        """
        pipeline = EvidencePipeline(
            feature_program=compile_feature_dsl(dsl),
            config=PipelineConfig(backend="memory"),
            adapter=MemoryKafkaAdapter(),
        )
        for source in ["collector-a", "collector-b"]:
            for i in range(12):
                risk = 1.0 if i % 2 else 0.0
                artifact = EvidenceArtifact(source=source, type="tls", data={"risk": risk, "label": bool(risk)})
                pipeline.ingest(artifact.to_dict())
                pipeline.process_one(timeout=0.01)

        graph = pipeline.state()["graph"]
        report = graph["cross_source_corroboration_test"]
        self.assertTrue(report["features"][0]["passed"])
        self.assertGreater(report["features"][0]["score"], 0.75)


if __name__ == "__main__":
    unittest.main()
