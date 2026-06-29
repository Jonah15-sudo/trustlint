import json
import os
import tempfile
import unittest

from spl_v7.causal import OnlineCausalGraphLearner
from spl_v7.dsl import compile_feature_dsl
from spl_v7.frontier import FrontierExplorer
from spl_v7.kafka_pipeline import EvidencePipeline, MemoryKafkaAdapter, PipelineConfig
from spl_v7.schema import EvidenceArtifact, EvidenceTransportMeta

from frontier.session import (
    CollapseDetector,
    ExplorationReport,
    ExplorationSession,
    compute_difficulty,
)


class DifficultyScoringTests(unittest.TestCase):
    def test_zero_mutations_returns_step_progression(self) -> None:
        score = compute_difficulty({"mutations": [], "mutation_count": 0}, step=3, max_steps=5)
        self.assertAlmostEqual(score, 0.6, places=4)

    def test_contradiction_raises_difficulty(self) -> None:
        low = compute_difficulty(
            {"mutations": [{"kind": "preserved_bool", "before": True, "after": True}], "mutation_count": 1},
            step=1, max_steps=3,
        )
        high = compute_difficulty(
            {"mutations": [{"kind": "flipped_bool", "before": True, "after": False}], "mutation_count": 1},
            step=1, max_steps=3,
        )
        self.assertGreater(high, low)

    def test_score_range_is_deterministic(self) -> None:
        summary = {
            "mutations": [
                {"kind": "flipped_bool", "before": True, "after": False},
                {"kind": "normalized_toward_midpoint", "before": 0.9, "after": 0.5},
            ],
            "mutation_count": 2,
        }
        a = compute_difficulty(summary, step=3, max_steps=5, frontier_pressure=0.4)
        b = compute_difficulty(summary, step=3, max_steps=5, frontier_pressure=0.4)
        self.assertEqual(a, b)
        self.assertGreaterEqual(a, 0.0)
        self.assertLessEqual(a, 1.0)

    def test_ambiguity_and_step_progression_increase_score(self) -> None:
        early = compute_difficulty(
            {"mutations": [{"kind": "preserved_bool", "before": True, "after": True}], "mutation_count": 1},
            step=1, max_steps=5,
        )
        late = compute_difficulty(
            {"mutations": [{"kind": "preserved_bool", "before": True, "after": True}], "mutation_count": 1},
            step=5, max_steps=5,
        )
        self.assertGreater(late, early)

    def test_frontier_pressure_amplifies_difficulty(self) -> None:
        base = compute_difficulty(
            {"mutations": [{"kind": "flipped_bool", "before": True, "after": False}], "mutation_count": 1},
            step=3, max_steps=5, frontier_pressure=0.0,
        )
        pressured = compute_difficulty(
            {"mutations": [{"kind": "flipped_bool", "before": True, "after": False}], "mutation_count": 1},
            step=3, max_steps=5, frontier_pressure=0.9,
        )
        self.assertGreater(pressured, base)


class ExplorationSessionTests(unittest.TestCase):
    def test_session_records_seed_and_challenges(self) -> None:
        seed = EvidenceArtifact(source="test", type="tls", data={"value": 1.0})
        session = ExplorationSession(seed)
        self.assertEqual(len(session.session_id), 16)
        self.assertEqual(session.seed_artifact["source"], "test")

    def test_add_challenge_appends_record(self) -> None:
        seed = EvidenceArtifact(source="test", type="tls", data={"value": 1.0})
        session = ExplorationSession(seed)
        challenge = _make_challenge(step=1, difficulty=0.5, challenge_id="c1")
        session.add_challenge(challenge)
        self.assertEqual(len(session.challenges), 1)
        self.assertEqual(session.challenges[0]["step"], 1)

    def test_confidence_progression(self) -> None:
        seed = EvidenceArtifact(source="test", type="tls", data={"value": 1.0})
        session = ExplorationSession(seed)
        for i in range(3):
            c = _make_challenge(step=i, difficulty=0.3 + i * 0.2, challenge_id=f"c{i}")
            session.add_challenge(c, {"causal_probability": 0.9 - i * 0.15})
        self.assertAlmostEqual(session.confidence_progression[0], 0.9)
        self.assertAlmostEqual(session.confidence_progression[1], 0.75)
        self.assertAlmostEqual(session.confidence_progression[2], 0.6, places=4)
        self.assertAlmostEqual(session.difficulty_progression[0], 0.3)
        self.assertAlmostEqual(session.difficulty_progression[1], 0.5)
        self.assertAlmostEqual(session.difficulty_progression[2], 0.7)

    def test_save_and_load_roundtrip(self) -> None:
        seed = EvidenceArtifact(source="test", type="tls", data={"value": 1.0})
        session = ExplorationSession(seed)
        for i in range(2):
            c = _make_challenge(step=i, difficulty=0.4 + i * 0.2, challenge_id=f"c{i}")
            session.add_challenge(c, {"causal_probability": 0.8 - i * 0.1})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
            session.save(f.name)

        loaded = ExplorationSession.load(path)
        self.assertEqual(loaded.session_id, session.session_id)
        self.assertEqual(len(loaded.challenges), 2)
        self.assertAlmostEqual(loaded.challenges[1]["difficulty"], 0.6, places=4)
        os.unlink(path)


class CollapseDetectionTests(unittest.TestCase):
    def test_no_collapse_for_stable_confidences(self) -> None:
        result = CollapseDetector.detect([0.9, 0.88, 0.85, 0.87], drop_threshold=0.20)
        self.assertIsNone(result)

    def test_detects_significant_drop(self) -> None:
        result = CollapseDetector.detect([0.95, 0.92, 0.87, 0.73, 0.48], drop_threshold=0.20)
        self.assertIsNotNone(result)
        self.assertTrue(result["detected"])
        self.assertGreaterEqual(result["drop_magnitude"], 0.20)
        self.assertEqual(result["peak_step"], 0)
        self.assertEqual(result["nadir_step"], 4)

    def test_ignores_small_drops(self) -> None:
        result = CollapseDetector.detect([0.9, 0.85, 0.82], drop_threshold=0.20)
        self.assertIsNone(result)

    def test_short_sequence_returns_none(self) -> None:
        self.assertIsNone(CollapseDetector.detect([0.9, 0.8]))


class ExplorationReportTests(unittest.TestCase):
    def test_generates_report_with_correct_metrics(self) -> None:
        seed = EvidenceArtifact(source="test", type="tls", data={"value": 1.0})
        session = ExplorationSession(seed)
        for i in range(4):
            c = _make_challenge(step=i, difficulty=0.3 + i * 0.15, challenge_id=f"c{i}")
            session.add_challenge(c, {"causal_probability": 0.9 - i * 0.12})

        report = ExplorationReport(session).generate()
        self.assertEqual(report["total_challenges"], 4)
        self.assertEqual(report["max_depth"], 4)
        self.assertAlmostEqual(report["average_difficulty"], 0.525, places=4)
        self.assertEqual(report["confidence_progression"], [0.9, 0.78, 0.66, 0.54])

    def test_report_includes_weaknesses_from_frontier(self) -> None:
        seed = EvidenceArtifact(source="test", type="tls", data={"value": 1.0})
        session = ExplorationSession(seed)
        c = _make_challenge(step=1, difficulty=0.5, challenge_id="c1")
        session.add_challenge(c, {"causal_probability": 0.8})

        frontier_report = {
            "weakest_features": [
                {"feature": "noise", "weakness": 0.72, "reliability": 0.28},
            ]
        }
        report = ExplorationReport(session).generate(frontier_report)
        self.assertEqual(len(report["discovered_weaknesses"]), 1)
        self.assertEqual(report["discovered_weaknesses"][0]["feature"], "noise")

    def test_save_json_writes_file(self) -> None:
        seed = EvidenceArtifact(source="test", type="tls", data={"value": 1.0})
        session = ExplorationSession(seed)
        c = _make_challenge(step=1, difficulty=0.5, challenge_id="c1")
        session.add_challenge(c, {"causal_probability": 0.8})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        report = ExplorationReport(session).save_json(path)
        self.assertTrue(os.path.exists(path))
        with open(path, "r") as f:
            loaded = json.load(f)
        self.assertEqual(loaded["session_id"], report["session_id"])
        os.unlink(path)


def _make_challenge(step: int, difficulty: float, challenge_id: str) -> object:
    from types import SimpleNamespace
    return SimpleNamespace(
        step=step,
        difficulty=difficulty,
        challenge_id=challenge_id,
        focus=["test"],
        mutation_summary={"mutations": [], "mutation_count": 0},
    )


if __name__ == "__main__":
    unittest.main()
