import json
import os
import tempfile
import unittest

from weakness_mapper.extractor import Weakness, WeaknessExtractor
from weakness_mapper.registry import WeaknessRegistry
from weakness_mapper.cluster import WeaknessClusterer
from weakness_mapper.boundaries import CapabilityBoundaryDetector
from weakness_mapper.reporter import CapabilityReporter


class WeaknessIdTests(unittest.TestCase):
    def test_same_inputs_same_id(self) -> None:
        a = Weakness(category="confidence_collapse", feature="", session_id="s1")
        b = Weakness(category="confidence_collapse", feature="", session_id="s2")
        self.assertEqual(a.weakness_id, b.weakness_id)

    def test_different_inputs_different_id(self) -> None:
        a = Weakness(category="confidence_collapse", feature="", session_id="s1")
        b = Weakness(category="feature_instability", feature="", session_id="s1")
        self.assertNotEqual(a.weakness_id, b.weakness_id)


class WeaknessFromDictTests(unittest.TestCase):
    def test_roundtrip_to_dict(self) -> None:
        w = Weakness(category="feature_instability", feature="hsts_missing", session_id="s1")
        w.reproducibility_count = 3
        d = w.to_dict()
        w2 = Weakness.from_dict(d)
        self.assertEqual(w.weakness_id, w2.weakness_id)
        self.assertEqual(w.category, w2.category)
        self.assertEqual(w.reproducibility_count, w2.reproducibility_count)
        self.assertEqual(w.session_ids, w2.session_ids)


class WeaknessExtractorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session_data = {
            "session_id": "test_session",
            "challenges": [
                {"step": 0, "difficulty": 0.59, "predicted_probability": 0.18, "decision": True, "features": {}},
                {"step": 1, "difficulty": 0.63, "predicted_probability": 0.60, "decision": False, "features": {}},
                {"step": 2, "difficulty": 0.67, "predicted_probability": 0.57, "decision": True, "features": {}},
                {"step": 3, "difficulty": 0.71, "predicted_probability": 0.66, "decision": False, "features": {}},
                {"step": 4, "difficulty": 0.75, "predicted_probability": 0.63, "decision": True, "features": {}},
            ],
        }
        self.report_data = {
            "collapse_detection": None,
            "discovered_weaknesses": [
                {"feature": "partial_flag", "weakness": 0.337, "reliability": 0.663},
            ],
        }

    def test_extracts_feature_instability(self) -> None:
        weaknesses = WeaknessExtractor.extract(self.session_data, self.report_data)
        categories = [w.category for w in weaknesses]
        self.assertIn("feature_instability", categories)

    def test_extracts_collapse_when_present(self) -> None:
        r = dict(self.report_data)
        r["collapse_detection"] = {
            "detected": True, "drop_magnitude": 0.58,
            "peak_step": 3, "nadir_step": 4,
            "peak_confidence": 0.96, "nadir_confidence": 0.38,
        }
        weaknesses = WeaknessExtractor.extract(self.session_data, r)
        categories = [w.category for w in weaknesses]
        self.assertIn("confidence_collapse", categories)

    def test_extracts_decision_oscillation(self) -> None:
        s = dict(self.session_data)
        s["challenges"] = [
            {"step": 0, "difficulty": 0.5, "predicted_probability": 0.9, "decision": True},
            {"step": 1, "difficulty": 0.6, "predicted_probability": 0.8, "decision": False},
            {"step": 2, "difficulty": 0.7, "predicted_probability": 0.7, "decision": True},
        ]
        weaknesses = WeaknessExtractor.extract(s, {"collapse_detection": None, "discovered_weaknesses": []})
        categories = [w.category for w in weaknesses]
        self.assertIn("decision_oscillation", categories)

    def test_extracts_low_confidence_region(self) -> None:
        s = dict(self.session_data)
        s["challenges"] = [
            {"step": 0, "difficulty": 0.59, "predicted_probability": 0.10, "decision": True},
        ]
        weaknesses = WeaknessExtractor.extract(s, {"collapse_detection": None, "discovered_weaknesses": []})
        categories = [w.category for w in weaknesses]
        self.assertIn("low_confidence_region", categories)

    def test_extracts_difficulty_threshold(self) -> None:
        s = dict(self.session_data)
        s["challenges"] = [
            {"step": 0, "difficulty": 0.59, "predicted_probability": 0.80, "decision": True},
            {"step": 1, "difficulty": 0.63, "predicted_probability": 0.20, "decision": False},
        ]
        weaknesses = WeaknessExtractor.extract(s, {"collapse_detection": None, "discovered_weaknesses": []})
        categories = [w.category for w in weaknesses]
        self.assertIn("difficulty_threshold", categories)


class WeaknessRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mktemp(suffix=".json")
        self.registry = WeaknessRegistry(self.tmp)

    def tearDown(self) -> None:
        if os.path.isfile(self.tmp):
            os.remove(self.tmp)

    def test_empty_registry(self) -> None:
        self.assertEqual(len(self.registry.get_all()), 0)

    def test_add_and_persist(self) -> None:
        w = Weakness(category="confidence_collapse", feature="", session_id="s1")
        self.registry.add(w)
        self.registry.save()
        reg2 = WeaknessRegistry(self.tmp)
        self.assertEqual(len(reg2.get_all()), 1)

    def test_add_duplicate_merges(self) -> None:
        w = Weakness(category="confidence_collapse", feature="", session_id="s1")
        self.registry.add(w)
        self.registry.add(w)
        self.assertEqual(len(self.registry.get_all()), 1)
        self.assertEqual(self.registry.get_all()[0].reproducibility_count, 2)

    def test_search_finds_match(self) -> None:
        w = Weakness(
            category="feature_instability",
            feature="hsts_missing",
            confidence_range=[0.1, 0.5],
            difficulty_range=[0.5, 0.8],
            session_id="s1",
        )
        self.registry.add(w)
        found = self.registry.search(
            category="feature_instability",
            feature="hsts_missing",
            confidence_range=[0.2, 0.4],
            difficulty_range=[0.6, 0.7],
        )
        self.assertIsNotNone(found)

    def test_search_no_match_different_category(self) -> None:
        w = Weakness(category="confidence_collapse", feature="", session_id="s1")
        self.registry.add(w)
        found = self.registry.search(
            category="feature_instability",
            feature="",
            confidence_range=[0.0, 1.0],
            difficulty_range=[0.0, 1.0],
        )
        self.assertIsNone(found)

    def test_add_weaknesses_returns_count(self) -> None:
        ws = [Weakness(category="confidence_collapse", feature="", session_id="s1")]
        added = self.registry.add_weaknesses(ws, "s1")
        self.assertEqual(added, 1)

    def test_clear_removes_all(self) -> None:
        w = Weakness(category="confidence_collapse", feature="", session_id="s1")
        self.registry.add(w)
        self.registry.clear()
        self.assertEqual(len(self.registry.get_all()), 0)

    def test_get_by_category(self) -> None:
        w1 = Weakness(category="confidence_collapse", feature="", session_id="s1")
        w2 = Weakness(category="feature_instability", feature="x", session_id="s1")
        self.registry.add(w1)
        self.registry.add(w2)
        collapses = self.registry.get_by_category("confidence_collapse")
        self.assertEqual(len(collapses), 1)
        self.assertEqual(collapses[0].category, "confidence_collapse")


class WeaknessClustererTests(unittest.TestCase):
    def test_empty_input(self) -> None:
        clusters = WeaknessClusterer.cluster([])
        self.assertEqual(len(clusters), 0)

    def test_clusters_by_category_and_feature(self) -> None:
        ws = [
            Weakness(category="confidence_collapse", feature="", session_id="s1"),
            Weakness(category="confidence_collapse", feature="", session_id="s2"),
            Weakness(category="feature_instability", feature="hsts_missing", session_id="s1"),
        ]
        clusters = WeaknessClusterer.cluster(ws)
        self.assertEqual(len(clusters), 2)

    def test_cluster_aggregates_reproducibility(self) -> None:
        ws = [
            Weakness(category="confidence_collapse", feature="", session_id="s1"),
            Weakness(category="confidence_collapse", feature="", session_id="s2"),
        ]
        clusters = WeaknessClusterer.cluster(ws)
        self.assertGreaterEqual(len(clusters), 1)
        self.assertEqual(clusters[0].reproducibility_count, 2)

    def test_cluster_collects_session_ids(self) -> None:
        ws = [
            Weakness(category="confidence_collapse", feature="", session_id="s1"),
            Weakness(category="confidence_collapse", feature="", session_id="s2"),
        ]
        clusters = WeaknessClusterer.cluster(ws)
        self.assertIn("s1", clusters[0].session_ids)
        self.assertIn("s2", clusters[0].session_ids)


class CapabilityBoundaryDetectorTests(unittest.TestCase):
    def test_identifies_collapse_zones(self) -> None:
        ws = [
            Weakness(category="confidence_collapse", feature="",
                     trigger_conditions={"drop_magnitude": 0.5},
                     session_id="s1"),
        ]
        b = CapabilityBoundaryDetector.detect(ws, None)
        self.assertEqual(len(b["confidence_collapse_zones"]), 1)

    def test_identifies_recurring_failures(self) -> None:
        ws = [
            Weakness(category="feature_instability", feature="partial_flag",
                     trigger_conditions={"weakness_score": 0.3, "reliability": 0.6},
                     session_id="s1"),
        ]
        ws[0].reproducibility_count = 2
        b = CapabilityBoundaryDetector.detect(ws, None)
        self.assertEqual(len(b["recurring_failure_regions"]), 1)

    def test_ignores_single_occurrence_failures(self) -> None:
        ws = [
            Weakness(category="feature_instability", feature="partial_flag",
                     trigger_conditions={"weakness_score": 0.3, "reliability": 0.6},
                     session_id="s1"),
        ]
        b = CapabilityBoundaryDetector.detect(ws, None)
        self.assertEqual(len(b["recurring_failure_regions"]), 0)

    def test_empty_input(self) -> None:
        b = CapabilityBoundaryDetector.detect([], None)
        self.assertEqual(len(b["confidence_collapse_zones"]), 0)


class CapabilityReporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mktemp(suffix=".json")
        self.registry = WeaknessRegistry(self.tmp)

    def tearDown(self) -> None:
        if os.path.isfile(self.tmp):
            os.remove(self.tmp)
        if os.path.isfile("test_report.json"):
            os.remove("test_report.json")

    def test_generates_report_with_metadata(self) -> None:
        w = Weakness(category="confidence_collapse", feature="", session_id="s1")
        self.registry.add(w)
        reporter = CapabilityReporter(self.registry)
        report = reporter.generate()
        self.assertIn("report_metadata", report)
        self.assertEqual(report["report_metadata"]["total_weaknesses"], 1)

    def test_strongest_areas_empty_when_no_data(self) -> None:
        reporter = CapabilityReporter(self.registry)
        report = reporter.generate()
        self.assertEqual(len(report["strongest_areas"]), 0)

    def test_weakest_areas_includes_instability(self) -> None:
        w = Weakness(category="feature_instability", feature="partial_flag", session_id="s1")
        self.registry.add(w)
        reporter = CapabilityReporter(self.registry)
        report = reporter.generate()
        self.assertGreaterEqual(len(report["weakest_areas"]), 1)

    def test_reproducible_count(self) -> None:
        w = Weakness(category="confidence_collapse", feature="", session_id="s1")
        w.reproducibility_count = 2
        self.registry.add(w)
        reporter = CapabilityReporter(self.registry)
        report = reporter.generate()
        self.assertEqual(report["report_metadata"]["reproducible_count"], 1)

    def test_save_json_writes_file(self) -> None:
        reporter = CapabilityReporter(self.registry)
        reporter.save_json("test_report.json")
        self.assertTrue(os.path.isfile("test_report.json"))
        with open("test_report.json") as f:
            data = json.load(f)
        self.assertIn("report_metadata", data)
