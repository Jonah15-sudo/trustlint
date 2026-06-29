import json
import os
import shutil
import tempfile
import unittest

from experiments.dsl_helpers import build_experiment_dsl
from experiments.metrics import MetricsCollector
from experiments.report import ExperimentReport
from weakness_mapper.extractor import Weakness
from frontier.session import CollapseDetector


class DSLBuilderTests(unittest.TestCase):
    def test_builds_all_12_features(self) -> None:
        prog = build_experiment_dsl()
        names = prog.ordered_feature_names()
        self.assertEqual(len(names), 12)
        self.assertIn("tls_valid", names)
        self.assertIn("ofe_contradiction_density", names)
        self.assertIn("ofe_topology_drift", names)
        self.assertIn("ofe_symbol_entropy", names)

    def test_evaluates_tls_context(self) -> None:
        prog = build_experiment_dsl()
        ctx = {
            "data": {"valid": True, "expiry_days": 7, "headers": {"hsts": False, "csp": True}},
            "transport_meta": {"status": "ok", "latency_ms": 90},
        }
        feats = prog.evaluate(ctx)
        self.assertEqual(feats["tls_valid"], True)
        self.assertEqual(feats["hsts_missing"], True)
        self.assertEqual(feats["ofe_contradiction_density"], 0.0)

    def test_evaluates_ofe_context(self) -> None:
        prog = build_experiment_dsl()
        ctx = {
            "data": {"signals": {"contradiction_density": 0.91, "topology_drift": 0.77, "symbol_entropy": 0.64}},
            "transport_meta": {"status": "ok"},
        }
        feats = prog.evaluate(ctx)
        self.assertAlmostEqual(feats["ofe_contradiction_density"], 0.91)
        self.assertAlmostEqual(feats["ofe_topology_drift"], 0.77)
        self.assertAlmostEqual(feats["ofe_symbol_entropy"], 0.64)
        self.assertEqual(feats["tls_valid"], False)


class AccuracyTests(unittest.TestCase):
    def test_all_correct(self) -> None:
        results = [{"decision": True}, {"decision": False}]
        labels = [True, False]
        a = MetricsCollector.accuracy(results, labels)
        self.assertEqual(a["accuracy"], 1.0)
        self.assertEqual(a["sample_size"], 2)

    def test_all_wrong(self) -> None:
        results = [{"decision": True}, {"decision": True}]
        labels = [False, False]
        a = MetricsCollector.accuracy(results, labels)
        self.assertEqual(a["accuracy"], 0.0)

    def test_skips_none_results(self) -> None:
        results = [None, {"decision": True}]
        labels = [True, True]
        a = MetricsCollector.accuracy(results, labels)
        self.assertEqual(a["accuracy"], 1.0)
        self.assertEqual(a["total_processed"], 2)
        self.assertEqual(a["total_predicted"], 1)

    def test_empty_input(self) -> None:
        a = MetricsCollector.accuracy([], [])
        self.assertEqual(a["accuracy"], 0.0)
        self.assertEqual(a["sample_size"], 0)

    def test_skips_none_labels(self) -> None:
        results = [{"decision": True}]
        labels = [None]
        a = MetricsCollector.accuracy(results, labels)
        self.assertEqual(a["total_predicted"], 0)


class FailureRateTests(unittest.TestCase):
    def test_no_failures(self) -> None:
        results = [{"decision": True}, {"decision": False}]
        f = MetricsCollector.failure_rate(results)
        self.assertEqual(f["error_rate"], 0.0)

    def test_half_failures(self) -> None:
        results = [None, {"decision": True}]
        f = MetricsCollector.failure_rate(results)
        self.assertEqual(f["error_rate"], 0.5)

    def test_all_failures(self) -> None:
        results = [None, None]
        f = MetricsCollector.failure_rate(results)
        self.assertEqual(f["error_rate"], 1.0)

    def test_empty(self) -> None:
        f = MetricsCollector.failure_rate([])
        self.assertEqual(f["error_rate"], 0.0)


class CalibrationTests(unittest.TestCase):
    def test_perfect_calibration(self) -> None:
        results = [{"causal_probability": 1.0, "decision": True}, {"causal_probability": 0.0, "decision": False}]
        labels = [True, False]
        c = MetricsCollector.confidence_calibration(results, labels)
        self.assertEqual(c["calibration_error"], 0.0)
        self.assertEqual(c["sample_size"], 2)

    def test_imperfect_calibration(self) -> None:
        results = [{"causal_probability": 0.9, "decision": True}, {"causal_probability": 0.8, "decision": False}]
        labels = [True, True]
        c = MetricsCollector.confidence_calibration(results, labels)
        self.assertGreater(c["calibration_error"], 0.0)

    def test_empty(self) -> None:
        c = MetricsCollector.confidence_calibration([], [])
        self.assertEqual(c["sample_size"], 0)


class WeaknessFrequencyTests(unittest.TestCase):
    def test_counts_features(self) -> None:
        ws = [
            Weakness(category="feature_instability", feature="partial_flag", session_id="s1"),
            Weakness(category="feature_instability", feature="partial_flag", session_id="s2"),
            Weakness(category="feature_instability", feature="http_error_flag", session_id="s1"),
            Weakness(category="confidence_collapse", feature="", session_id="s1"),
        ]
        freq = MetricsCollector.weakness_frequency(ws, ["partial_flag", "http_error_flag", "hsts_missing"], total_weaknesses=4)
        self.assertEqual(len(freq), 3)
        pf = [x for x in freq if x["weakness"] == "partial_flag"][0]
        self.assertEqual(pf["frequency"], 2)
        self.assertEqual(pf["percent_of_total"], 50.0)
        hf = [x for x in freq if x["weakness"] == "http_error_flag"][0]
        self.assertEqual(hf["frequency"], 1)
        self.assertEqual(hf["percent_of_total"], 25.0)

    def test_empty(self) -> None:
        freq = MetricsCollector.weakness_frequency([], ["partial_flag"], total_weaknesses=0)
        self.assertEqual(freq[0]["frequency"], 0)


class DifficultyDistributionTests(unittest.TestCase):
    def test_bucket_allocation(self) -> None:
        results = [
            {"decision": True},
            {"decision": False},
            {"decision": True},
            {"decision": True},
        ]
        difficulties = [0.1, 0.4, 0.6, 0.8]
        labels = [True, True, True, True]
        dd = MetricsCollector.difficulty_distribution(results, difficulties, labels)
        self.assertIn("low_00_03", dd)
        self.assertIn("mid_03_05", dd)
        self.assertIn("mid_05_07", dd)
        self.assertIn("high_07_10", dd)
        self.assertEqual(dd["low_00_03"]["count"], 1)
        self.assertEqual(dd["mid_03_05"]["count"], 1)
        self.assertEqual(dd["mid_05_07"]["count"], 1)
        self.assertEqual(dd["high_07_10"]["count"], 1)

    def test_accuracy_per_bucket(self) -> None:
        results = [{"decision": True}, {"decision": False}]
        difficulties = [0.1, 0.4]
        labels = [True, True]
        dd = MetricsCollector.difficulty_distribution(results, difficulties, labels)
        self.assertEqual(dd["low_00_03"]["accuracy"], 1.0)
        self.assertEqual(dd["mid_03_05"]["accuracy"], 0.0)


class CapabilityBoundaryTests(unittest.TestCase):
    def test_no_crossings_when_all_above(self) -> None:
        conf = [0.9, 0.8, 0.85]
        diff = [0.5, 0.6, 0.7]
        cb = MetricsCollector.capability_boundary_position(conf, diff, confidence_threshold=0.5)
        self.assertEqual(cb["fraction_below"], 0.0)
        self.assertEqual(len(cb["crossings"]), 0)

    def test_detects_down_crossing(self) -> None:
        conf = [0.9, 0.3, 0.2]
        diff = [0.5, 0.6, 0.7]
        cb = MetricsCollector.capability_boundary_position(conf, diff, confidence_threshold=0.5)
        self.assertGreater(cb["fraction_below"], 0.0)
        self.assertGreaterEqual(len(cb["crossings"]), 1)

    def test_empty_input(self) -> None:
        cb = MetricsCollector.capability_boundary_position([], [])
        self.assertEqual(cb["sample_size"], 0)


class ComputeDeltasTests(unittest.TestCase):
    def test_improvement(self) -> None:
        d = MetricsCollector.compute_deltas(0.5, 0.7)
        self.assertEqual(d["direction"], "improvement")
        self.assertEqual(d["absolute_difference"], 0.2)

    def test_regression(self) -> None:
        d = MetricsCollector.compute_deltas(0.7, 0.5)
        self.assertEqual(d["direction"], "regression")
        self.assertEqual(d["absolute_difference"], -0.2)

    def test_unchanged(self) -> None:
        d = MetricsCollector.compute_deltas(0.5, 0.5)
        self.assertEqual(d["direction"], "unchanged")

    def test_zero_division(self) -> None:
        d = MetricsCollector.compute_deltas(0.0, 0.5)
        self.assertEqual(d["absolute_difference"], 0.5)
        self.assertEqual(d["percentage_difference"], 0.0)

    def test_lower_is_better_improvement(self) -> None:
        d = MetricsCollector.compute_deltas(0.7, 0.5, lower_is_better=True)
        self.assertEqual(d["direction"], "improvement")
        self.assertEqual(d["absolute_difference"], -0.2)

    def test_lower_is_better_regression(self) -> None:
        d = MetricsCollector.compute_deltas(0.5, 0.7, lower_is_better=True)
        self.assertEqual(d["direction"], "regression")
        self.assertEqual(d["absolute_difference"], 0.2)


class CollapseDetectorTests(unittest.TestCase):
    def test_detects_collapse(self) -> None:
        result = CollapseDetector.detect([0.9, 0.85, 0.3, 0.2], drop_threshold=0.20)
        self.assertIsNotNone(result)
        self.assertTrue(result["detected"])

    def test_ignores_stable(self) -> None:
        result = CollapseDetector.detect([0.9, 0.85, 0.8, 0.75], drop_threshold=0.20)
        self.assertIsNone(result)


class ExperimentReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _result(self) -> dict:
        return {
            "metadata": {
                "experiment": "OFE Campaign",
                "condition_a": "A",
                "condition_b": "B",
                "training_items": 90,
                "ofe_signals": 12,
                "curricula": ["test"],
                "total_challenges": 25,
            },
            "baseline": {
                "accuracy": {"accuracy": 0.6, "sample_size": 25, "total_processed": 25, "total_predicted": 25, "correct": 15},
                "failure_rate": {"total": 25, "errors": 0, "error_rate": 0.0},
                "calibration": {"sample_size": 25, "calibration_error": 0.4, "ece": 0.35, "mean_confidence": 0.5, "accuracy": 0.6},
                "weakness_frequency": [{"weakness": "partial_flag", "frequency": 5, "percent_of_total": 27.8}],
                "total_weaknesses": 18,
                "weakness_counts": {"partial_flag": 5, "http_error_flag": 5, "hsts_missing": 0},
                "collapse": {"total_sequences": 5, "collapse_count": 1, "collapse_rate": 0.2, "mean_drop_magnitude": 0.3},
                "difficulty_distribution": {
                    "low_00_03": {"range": "0.0-0.3", "count": 5, "correct": 3, "accuracy": 0.6, "mean_confidence": 0.5},
                    "mid_03_05": {"range": "0.3-0.5", "count": 10, "correct": 6, "accuracy": 0.6, "mean_confidence": 0.5},
                    "mid_05_07": {"range": "0.5-0.7", "count": 10, "correct": 6, "accuracy": 0.6, "mean_confidence": 0.5},
                    "high_07_10": {"range": "0.7-1.0", "count": 0, "correct": 0, "accuracy": 0.0, "mean_confidence": 0.0},
                },
                "capability_boundary": {"confidence_threshold": 0.5, "fraction_below": 0.24, "sample_size": 25, "crossings": [{"difficulty": 0.65, "direction": "down"}]},
            },
            "ofe": {
                "accuracy": {"accuracy": 0.6, "sample_size": 25, "total_processed": 25, "total_predicted": 25, "correct": 15},
                "failure_rate": {"total": 25, "errors": 0, "error_rate": 0.0},
                "calibration": {"sample_size": 25, "calibration_error": 0.39, "ece": 0.34, "mean_confidence": 0.5, "accuracy": 0.6},
                "weakness_frequency": [{"weakness": "partial_flag", "frequency": 2, "percent_of_total": 11.1}],
                "total_weaknesses": 18,
                "weakness_counts": {"partial_flag": 2, "http_error_flag": 0, "hsts_missing": 0},
                "collapse": {"total_sequences": 5, "collapse_count": 1, "collapse_rate": 0.2, "mean_drop_magnitude": 0.3},
                "difficulty_distribution": {
                    "low_00_03": {"range": "0.0-0.3", "count": 5, "correct": 3, "accuracy": 0.6, "mean_confidence": 0.5},
                    "mid_03_05": {"range": "0.3-0.5", "count": 10, "correct": 6, "accuracy": 0.6, "mean_confidence": 0.5},
                    "mid_05_07": {"range": "0.5-0.7", "count": 10, "correct": 6, "accuracy": 0.6, "mean_confidence": 0.5},
                    "high_07_10": {"range": "0.7-1.0", "count": 0, "correct": 0, "accuracy": 0.0, "mean_confidence": 0.0},
                },
                "capability_boundary": {"confidence_threshold": 0.5, "fraction_below": 0.20, "sample_size": 25, "crossings": [{"difficulty": 0.68, "direction": "down"}]},
            },
            "comparison": {
                "accuracy": {"A": 0.6, "B": 0.6, "absolute_difference": 0.0, "percentage_difference": 0.0, "direction": "unchanged"},
                "calibration_error": {"A": 0.4, "B": 0.39, "absolute_difference": -0.01, "percentage_difference": -2.5, "direction": "improvement"},
                "error_rate": {"A": 0.0, "B": 0.0, "absolute_difference": 0.0, "percentage_difference": 0.0, "direction": "unchanged"},
                "collapse_rate": {"A": 0.2, "B": 0.2, "absolute_difference": 0.0, "percentage_difference": 0.0, "direction": "unchanged"},
                "total_weaknesses": {"A": 18.0, "B": 18.0, "absolute_difference": 0.0, "percentage_difference": 0.0, "direction": "unchanged"},
                "weakness_level": [
                    {"weakness": "partial_flag", "a_frequency": 5, "b_frequency": 2, "a_percent": 27.8, "b_percent": 11.1, "absolute_difference": -3, "percentage_point_difference": -16.7, "interpretation": "improvement"},
                    {"weakness": "http_error_flag", "a_frequency": 5, "b_frequency": 0, "a_percent": 27.8, "b_percent": 0.0, "absolute_difference": -5, "percentage_point_difference": -27.8, "interpretation": "improvement"},
                    {"weakness": "hsts_missing", "a_frequency": 0, "b_frequency": 0, "a_percent": 0.0, "b_percent": 0.0, "absolute_difference": 0, "percentage_point_difference": 0.0, "interpretation": "unchanged"},
                ],
                "difficulty_distribution": {
                    "low_00_03": {"A_accuracy": 0.6, "B_accuracy": 0.6, "absolute_difference": 0.0},
                },
                "capability_boundary": {"a_fraction_below": 0.24, "b_fraction_below": 0.20, "delta_fraction_below": -0.04},
            },
        }

    def test_save_json_writes_file(self) -> None:
        path = os.path.join(self.tmpdir, "results.json")
        r = ExperimentReport(self._result(), raw_dir=self.tmpdir)
        r.save_json(path)
        self.assertTrue(os.path.isfile(path))
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["baseline"]["accuracy"]["accuracy"], 0.6)

    def test_save_markdown_writes_file(self) -> None:
        path = os.path.join(self.tmpdir, "report.md")
        r = ExperimentReport(self._result(), raw_dir=self.tmpdir)
        r.save_markdown(path)
        self.assertTrue(os.path.isfile(path))
        with open(path) as f:
            text = f.read()
        self.assertIn("OFE Experimental Campaign", text)
        self.assertIn("Accuracy", text)

    def test_markdown_includes_weakness_table(self) -> None:
        path = os.path.join(self.tmpdir, "report.md")
        r = ExperimentReport(self._result(), raw_dir=self.tmpdir)
        r.save_markdown(path)
        with open(path) as f:
            text = f.read()
        self.assertIn("http_error_flag", text)
        self.assertIn("partial_flag", text)

    def test_markdown_answers_all_7_questions(self) -> None:
        path = os.path.join(self.tmpdir, "report.md")
        r = ExperimentReport(self._result(), raw_dir=self.tmpdir)
        r.save_markdown(path)
        with open(path) as f:
            text = f.read()
        for i in range(1, 8):
            self.assertIn(f"## {i}.", text)
