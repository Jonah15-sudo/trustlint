import json
import os
import tempfile
import unittest

from frontier.metrics import compute_difficulty, CollapseDetector
from frontier.reports import ExplorationReport
from frontier.session import ExplorationSession
from spl_v7.schema import EvidenceArtifact


class FrontierMetricsContractTests(unittest.TestCase):
    def test_metrics_module_imports_cleanly(self) -> None:
        from frontier.metrics import compute_difficulty, CollapseDetector
        self.assertTrue(callable(compute_difficulty))
        self.assertTrue(hasattr(CollapseDetector, "detect"))

    def test_difficulty_scores_identical_to_previous(self) -> None:
        summary = {
            "mutations": [
                {"kind": "flipped_bool", "before": True, "after": False},
                {"kind": "normalized_toward_midpoint", "before": 0.9, "after": 0.5},
            ],
            "mutation_count": 2,
        }
        result = compute_difficulty(summary, step=3, max_steps=5, frontier_pressure=0.4)
        self.assertAlmostEqual(result, 0.6050, places=4)

    def test_collapse_detection_identical_to_previous(self) -> None:
        result = CollapseDetector.detect([0.95, 0.92, 0.87, 0.73, 0.48], drop_threshold=0.20)
        self.assertIsNotNone(result)
        self.assertTrue(result["detected"])
        self.assertAlmostEqual(result["drop_magnitude"], 0.47, places=4)
        self.assertEqual(result["peak_step"], 0)
        self.assertEqual(result["nadir_step"], 4)

    def test_no_collapse_for_stable_confidences(self) -> None:
        result = CollapseDetector.detect([0.9, 0.88, 0.85, 0.87], drop_threshold=0.20)
        self.assertIsNone(result)

    def test_short_sequence_returns_none(self) -> None:
        self.assertIsNone(CollapseDetector.detect([0.9, 0.8]))


class FrontierReportsContractTests(unittest.TestCase):
    def test_reports_module_imports_cleanly(self) -> None:
        from frontier.reports import ExplorationReport
        self.assertTrue(hasattr(ExplorationReport, "generate"))
        self.assertTrue(hasattr(ExplorationReport, "save_json"))

    def test_report_json_schema_compatible(self) -> None:
        seed = EvidenceArtifact(source="test", type="tls", data={"value": 1.0})
        session = ExplorationSession(seed)
        self._add_challenge(session, step=0, diff=0.3, conf=0.9)
        self._add_challenge(session, step=1, diff=0.5, conf=0.75)
        self._add_challenge(session, step=2, diff=0.7, conf=0.6)

        report = ExplorationReport(session).generate()
        self.assertIn("session_id", report)
        self.assertIn("total_challenges", report)
        self.assertIn("average_difficulty", report)
        self.assertIn("difficulty_progression", report)
        self.assertIn("confidence_progression", report)
        self.assertIn("collapse_detection", report)
        self.assertIn("discovered_weaknesses", report)
        self.assertEqual(report["total_challenges"], 3)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        report2 = ExplorationReport(session).save_json(path)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            loaded = json.load(f)
        self.assertEqual(loaded["session_id"], report2["session_id"])
        self.assertEqual(loaded["total_challenges"], 3)
        os.unlink(path)

    def test_report_includes_weaknesses_from_frontier(self) -> None:
        seed = EvidenceArtifact(source="test", type="tls", data={"value": 1.0})
        session = ExplorationSession(seed)
        self._add_challenge(session, step=0, diff=0.5, conf=0.8)

        frontier_info = {
            "weakest_features": [
                {"feature": "noise", "weakness": 0.72, "reliability": 0.28},
            ]
        }
        report = ExplorationReport(session).generate(frontier_info)
        self.assertEqual(len(report["discovered_weaknesses"]), 1)
        self.assertEqual(report["discovered_weaknesses"][0]["feature"], "noise")

    def _add_challenge(self, session, step: int, diff: float, conf: float) -> None:
        from types import SimpleNamespace
        c = SimpleNamespace(
            step=step, difficulty=diff,
            challenge_id=f"c{step}",
            focus=["test"],
            mutation_summary={"mutations": [], "mutation_count": 0},
        )
        session.add_challenge(c, {"causal_probability": conf, "decision": conf >= 0.5})


class FrontierBackwardCompatContractTests(unittest.TestCase):
    def test_old_import_paths_still_work(self) -> None:
        from frontier.session import compute_difficulty, ExplorationSession, ExplorationReport, CollapseDetector
        self.assertTrue(callable(compute_difficulty))
        self.assertTrue(hasattr(CollapseDetector, "detect"))
        self.assertTrue(hasattr(ExplorationReport, "generate"))
        self.assertTrue(hasattr(ExplorationSession, "add_challenge"))

    def test_new_import_paths_work(self) -> None:
        from frontier.metrics import compute_difficulty, CollapseDetector
        from frontier.reports import ExplorationReport
        from frontier.session import ExplorationSession
        self.assertTrue(callable(compute_difficulty))
        self.assertTrue(hasattr(CollapseDetector, "detect"))
        self.assertTrue(hasattr(ExplorationReport, "generate"))
        self.assertTrue(hasattr(ExplorationSession, "add_challenge"))

    def test_no_spl_core_imports_in_frontier(self) -> None:
        import frontier.metrics
        import frontier.reports
        import frontier.session

        for mod in [frontier.metrics, frontier.reports, frontier.session]:
            mod_name = mod.__name__
            for name, obj in vars(mod).items():
                if hasattr(obj, "__module__"):
                    core_modules = ["spl_v7.causal", "spl_v7.dsl", "spl_v7.kafka_pipeline",
                                    "spl_v7.frontier", "spl_v7.verification", "spl_v7.dashboard"]
                    for core in core_modules:
                        self.assertFalse(
                            obj.__module__.startswith(core),
                            f"{mod_name} imports from {core} via {name}",
                        )


if __name__ == "__main__":
    unittest.main()
