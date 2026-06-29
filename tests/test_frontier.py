import unittest

from spl_v7.causal import OnlineCausalGraphLearner
from spl_v7.dsl import compile_feature_dsl
from spl_v7.frontier import FrontierExplorer
from spl_v7.kafka_pipeline import EvidencePipeline, MemoryKafkaAdapter, PipelineConfig
from spl_v7.schema import EvidenceArtifact, EvidenceTransportMeta


class FrontierExplorerTests(unittest.TestCase):
    def _build_trained_pipeline(self) -> EvidencePipeline:
        dsl = """
        feature signal = data.signal
        feature noise = data.noise
        feature combined = clamp(0.0, 1.0, 0.8 * signal + 0.2 * noise)
        """
        program = compile_feature_dsl(dsl)
        learner = OnlineCausalGraphLearner()
        pipeline = EvidencePipeline(
            feature_program=program,
            causal_graph=learner,
            config=PipelineConfig(backend="memory"),
            adapter=MemoryKafkaAdapter(),
        )
        for i in range(80):
            signal = 1.0 if i % 2 else 0.0
            noise = (i * 7 % 10) / 10.0
            artifact = EvidenceArtifact(
                source="collector",
                type="structured",
                data={"signal": signal, "noise": noise, "label": bool(signal)},
                transport_meta=EvidenceTransportMeta(status="ok"),
            )
            pipeline.ingest(artifact.to_dict())
            pipeline.process_one(timeout=0.05)
        return pipeline

    def test_structural_signal_bridge_runs_through_pipeline(self) -> None:
        dsl = """
        feature contradiction_density = data.signals.contradiction_density
        feature topology_drift = data.signals.topology_drift
        feature frontier_pressure = clamp(0.0, 1.0, 0.6 * contradiction_density + 0.4 * topology_drift)
        """
        program = compile_feature_dsl(dsl)
        pipeline = EvidencePipeline(
            feature_program=program,
            causal_graph=OnlineCausalGraphLearner(),
            config=PipelineConfig(backend="memory"),
            adapter=MemoryKafkaAdapter(),
        )
        explorer = FrontierExplorer(pipeline, signal_source="ofe")
        artifact = explorer.wrap_structural_signals(
            {"contradiction_density": 0.91, "topology_drift": 0.77, "symbol_entropy": 0.64},
            source="ofe",
            label=True,
        )

        pipeline.ingest(artifact.to_dict())
        output = pipeline.process_one(timeout=0.05)
        self.assertIsNotNone(output)
        self.assertEqual(output["source"], "ofe")
        self.assertIn("frontier_pressure", output["features"])
        self.assertGreater(output["features"]["frontier_pressure"], 0.0)
        self.assertTrue(output["verification"]["passed"])

    def test_curriculum_generation_targets_weak_feature_and_preserves_seed(self) -> None:
        pipeline = self._build_trained_pipeline()
        explorer = FrontierExplorer(pipeline)
        seed = EvidenceArtifact(
            source="collector",
            type="structured",
            data={"signal": True, "noise": 0.1, "label": True},
            transport_meta=EvidenceTransportMeta(status="ok"),
        )
        original = seed.to_dict()
        report = explorer.analyze_frontier()
        weakest_features = {item["feature"] for item in report["weakest_features"]}
        curriculum = explorer.generate_curriculum(seed, steps=3)

        self.assertEqual(seed.to_dict(), original)
        self.assertEqual(len(curriculum), 3)
        self.assertTrue(all(item.difficulty <= curriculum[-1].difficulty for item in curriculum))
        self.assertTrue(any(item.focus for item in curriculum))
        self.assertTrue(any("noise" in item.focus for item in curriculum) or "noise" in weakest_features)
        self.assertTrue(any(item.mutation_summary["changed_paths"] for item in curriculum))
        self.assertNotEqual(curriculum[0].artifact.data, seed.data)
        self.assertEqual(len({item.challenge_id for item in curriculum}), 3)


if __name__ == "__main__":
    unittest.main()
