import json
import os
import tempfile
import unittest

from experiments.replication import ReplicationRunner, _mean, _stdev, _cohens_d, _ci95
from experiments.replication_report import _question_answers
from experiments.promotion_readiness import _classify, _classify_weakness
from experiments.stability import WeaknessStabilityAnalyzer, ConfidenceStabilityAnalyzer


class StatsTests(unittest.TestCase):
    def test_mean_positive(self) -> None:
        self.assertAlmostEqual(_mean([1, 2, 3, 4, 5]), 3.0)

    def test_mean_empty(self) -> None:
        self.assertEqual(_mean([]), 0.0)

    def test_stdev_positive(self) -> None:
        self.assertAlmostEqual(_stdev([1, 1, 1, 1]), 0.0)
        self.assertAlmostEqual(_stdev([1, 2, 3]), 1.0)

    def test_stdev_insufficient(self) -> None:
        self.assertEqual(_stdev([5]), 0.0)

    def test_cohens_d_zero_variance(self) -> None:
        self.assertEqual(_cohens_d([5, 5, 5], [1, 1, 1]), 0.0)

    def test_cohens_d_positive(self) -> None:
        d = _cohens_d([1, 2, 3], [4, 5, 6])
        self.assertGreater(d, 0)

    def test_cohens_d_insufficient_samples(self) -> None:
        self.assertEqual(_cohens_d([1], [2]), 0.0)

    def test_ci95_small(self) -> None:
        lo, hi = _ci95([1, 2, 3])
        self.assertLess(lo, hi)

    def test_ci95_insufficient(self) -> None:
        lo, hi = _ci95([5])
        self.assertEqual(lo, 0.0)
        self.assertEqual(hi, 0.0)


class ReplicationRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.runner = ReplicationRunner(campaign_count=2, raw_dir=self.tmpdir)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmpdir)

    def _make_campaign(self, accuracy_a: float = 0.84, accuracy_b: float = 0.84,
                       calib_a: float = 0.33, calib_b: float = 0.34,
                       collapse_a: float = 0.2, collapse_b: float = 0.2,
                       weakness_counts: tuple = (5, 1)) -> dict:
        wa, wb = weakness_counts
        return {
            "metadata": {"total_challenges": 25},
            "baseline": {
                "accuracy": {"accuracy": accuracy_a},
                "calibration": {"calibration_error": calib_a},
                "collapse": {"collapse_rate": collapse_a},
                "total_weaknesses": wa,
                "weakness_counts": {"partial_flag": wa, "http_error_flag": wa, "hsts_missing": 0},
            },
            "ofe": {
                "accuracy": {"accuracy": accuracy_b},
                "calibration": {"calibration_error": calib_b},
                "collapse": {"collapse_rate": collapse_b},
                "total_weaknesses": wb,
                "weakness_counts": {"partial_flag": wb, "http_error_flag": wb, "hsts_missing": 0},
            },
            "comparison": {
                "accuracy": {"absolute_difference": accuracy_b - accuracy_a,
                             "percentage_difference": 0, "a_value": accuracy_a, "b_value": accuracy_b},
                "calibration_error": {"absolute_difference": calib_b - calib_a,
                                      "percentage_difference": 0, "a_value": calib_a, "b_value": calib_b,
                                      "lower_is_better": True},
                "error_rate": {"absolute_difference": 0, "percentage_difference": 0},
                "collapse_rate": {"absolute_difference": collapse_b - collapse_a,
                                  "percentage_difference": 0, "a_value": collapse_a, "b_value": collapse_b,
                                  "lower_is_better": True},
                "total_weaknesses": {"absolute_difference": float(wb - wa),
                                     "percentage_difference": 0, "a_value": float(wa), "b_value": float(wb),
                                     "lower_is_better": True},
                "weakness_level": [
                    {"weakness": "partial_flag", "a_frequency": wa, "b_frequency": wb,
                     "absolute_difference": wb - wa},
                    {"weakness": "http_error_flag", "a_frequency": wa, "b_frequency": wb,
                     "absolute_difference": wb - wa},
                    {"weakness": "hsts_missing", "a_frequency": 0, "b_frequency": 0,
                     "absolute_difference": 0},
                ],
            },
        }

    def test_aggregate_single_campaign(self) -> None:
        c = self._make_campaign()
        agg = self.runner._aggregate([c])
        self.assertEqual(agg["metadata"]["campaign_count"], 1)
        self.assertEqual(len(agg["metric_summaries"]), 5)

    def test_aggregate_two_campaigns(self) -> None:
        c1 = self._make_campaign(accuracy_a=0.84, accuracy_b=0.90)
        c2 = self._make_campaign(accuracy_a=0.84, accuracy_b=0.86)
        agg = self.runner._aggregate([c1, c2])
        am = next(m for m in agg["metric_summaries"] if m["key"] == "accuracy_delta")
        # mean accuracy delta = ((0.90-0.84) + (0.86-0.84)) / 2 = 0.04
        self.assertAlmostEqual(am["mean_delta"], 0.04, places=4)
        self.assertEqual(am["improvement_count"], 2)

    def test_aggregate_accuracy_not_improving(self) -> None:
        c1 = self._make_campaign(accuracy_a=0.84, accuracy_b=0.80)
        c2 = self._make_campaign(accuracy_a=0.84, accuracy_b=0.82)
        agg = self.runner._aggregate([c1, c2])
        am = next(m for m in agg["metric_summaries"] if m["key"] == "accuracy_delta")
        self.assertEqual(am["improvement_count"], 0)

    def test_weakness_summaries_repeated(self) -> None:
        c1 = self._make_campaign(weakness_counts=(5, 0))
        c2 = self._make_campaign(weakness_counts=(5, 0))
        agg = self.runner._aggregate([c1, c2])
        ws = next(w for w in agg["weakness_summaries"] if w["weakness"] == "http_error_flag")
        self.assertEqual(ws["mean_a_frequency"], 5.0)
        self.assertEqual(ws["mean_b_frequency"], 0.0)
        self.assertEqual(ws["replication_rate"], 1.0)
        self.assertEqual(ws["reproducibility"], "repeated")

    def test_weakness_summaries_never_found(self) -> None:
        c1 = self._make_campaign(weakness_counts=(0, 0))
        c2 = self._make_campaign(weakness_counts=(0, 0))
        agg = self.runner._aggregate([c1, c2])
        ws = next(w for w in agg["weakness_summaries"] if w["weakness"] == "hsts_missing")
        self.assertEqual(ws["reproducibility"], "not_repeated")


class ReplicationReportTests(unittest.TestCase):
    def test_question_answers_accuracy_not_repeated(self) -> None:
        agg = {
            "metadata": {"campaign_count": 2, "challenges_per_campaign": 25},
            "metric_summaries": [
                {"metric": "Accuracy Δ", "key": "accuracy_delta", "lower_is_better": False,
                 "campaign_count": 2,
                 "mean_delta": -0.06, "std_delta": 0.01, "ci_95_lo": -0.08, "ci_95_hi": -0.04,
                 "cohens_d": -1.0, "improvement_count": 0, "regression_count": 2,
                 "replication_rate": 0.0, "reproducibility": "not_repeated"},
                {"metric": "Calibration Error Δ", "key": "calibration_delta", "lower_is_better": True,
                 "campaign_count": 2,
                 "mean_delta": 0.01, "std_delta": 0.0, "ci_95_lo": 0.0, "ci_95_hi": 0.01,
                 "cohens_d": 1.0, "improvement_count": 0, "regression_count": 2,
                 "replication_rate": 0.0, "reproducibility": "not_repeated"},
                {"metric": "Error Rate Δ", "key": "error_rate_delta", "lower_is_better": True,
                 "campaign_count": 2,
                 "mean_delta": 0.0, "std_delta": 0.0, "ci_95_lo": 0.0, "ci_95_hi": 0.0,
                 "cohens_d": 0.0, "improvement_count": 0, "regression_count": 2,
                 "replication_rate": 0.0, "reproducibility": "not_repeated"},
                {"metric": "Collapse Rate Δ", "key": "collapse_rate_delta", "lower_is_better": True,
                 "campaign_count": 2,
                 "mean_delta": 0.0, "std_delta": 0.0, "ci_95_lo": 0.0, "ci_95_hi": 0.0,
                 "cohens_d": 0.0, "improvement_count": 0, "regression_count": 2,
                 "replication_rate": 0.0, "reproducibility": "not_repeated"},
                {"metric": "Weakness Count Δ", "key": "weakness_count_delta", "lower_is_better": True,
                 "campaign_count": 2,
                 "mean_delta": 0.0, "std_delta": 0.0, "ci_95_lo": 0.0, "ci_95_hi": 0.0,
                 "cohens_d": 0.0, "improvement_count": 0, "regression_count": 2,
                 "replication_rate": 0.0, "reproducibility": "not_repeated"},
            ],
            "weakness_summaries": [
                {"weakness": "partial_flag", "campaign_count": 2, "mean_a_frequency": 5.0,
                 "mean_b_frequency": 0.0, "mean_difference": -5.0, "replication_rate": 1.0,
                 "campaigns_with_improvement": 2, "reproducibility": "repeated"},
                {"weakness": "http_error_flag", "campaign_count": 2, "mean_a_frequency": 5.0,
                 "mean_b_frequency": 0.0, "mean_difference": -5.0, "replication_rate": 1.0,
                 "campaigns_with_improvement": 2, "reproducibility": "repeated"},
                {"weakness": "hsts_missing", "campaign_count": 2, "mean_a_frequency": 0.0,
                 "mean_b_frequency": 0.0, "mean_difference": 0.0, "replication_rate": 0.0,
                 "campaigns_with_improvement": 0, "reproducibility": "not_repeated"},
            ],
        }
        qa = _question_answers(agg)
        self.assertEqual(len(qa), 7)
        # Q6: 2 repeated, 1 disappeared
        self.assertIn("partial_flag, http_error_flag", qa[5]["analysis"])
        self.assertIn("hsts_missing", qa[5]["analysis"])


class PromotionReadinessTests(unittest.TestCase):
    def test_classify_metric_promote(self) -> None:
        self.assertEqual(_classify(0.8, 0.5, 10, 12, False), "PROMOTE")

    def test_classify_metric_reject(self) -> None:
        self.assertEqual(_classify(0.2, 1.0, 2, 10, False), "REJECT")

    def test_classify_metric_hold(self) -> None:
        self.assertEqual(_classify(0.5, 0.1, 6, 12, False), "HOLD")

    def test_classify_weakness_promote_high_rate(self) -> None:
        self.assertEqual(_classify_weakness(5.0, 0.0, 1.0, -0.5), "PROMOTE")

    def test_classify_weakness_zero_variance(self) -> None:
        """100% identical improvement with undefined d should still promote."""
        self.assertEqual(_classify_weakness(5.0, 0.0, 1.0, 0.0), "PROMOTE")

    def test_classify_weakness_reject_no_change(self) -> None:
        self.assertEqual(_classify_weakness(3.0, 3.0, 0.0, 0.0), "REJECT")

    def test_classify_weakness_hold_mixed(self) -> None:
        self.assertEqual(_classify_weakness(5.0, 3.0, 0.5, -0.1), "HOLD")

    def test_classify_weakness_reject_low_rate(self) -> None:
        self.assertEqual(_classify_weakness(5.0, 4.0, 0.2, -0.3), "REJECT")

    def test_classify_weakness_regression_high_rate(self) -> None:
        self.assertEqual(_classify_weakness(0.0, 5.0, 0.9, 1.0), "REJECT")


class WeaknessStabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = WeaknessStabilityAnalyzer(["partial_flag", "http_error_flag"])

    def test_identical_reduction(self) -> None:
        bl = [{"partial_flag": 5, "http_error_flag": 5} for _ in range(5)]
        ofe = [{"partial_flag": 0, "http_error_flag": 0} for _ in range(5)]
        r = self.analyzer.analyze(bl, ofe)
        for name in ["partial_flag", "http_error_flag"]:
            self.assertEqual(r[name]["replication_rate"], 1.0)
            self.assertEqual(r[name]["status"], "repeated")

    def test_no_change(self) -> None:
        bl = [{"partial_flag": 5, "http_error_flag": 5} for _ in range(5)]
        ofe = [{"partial_flag": 5, "http_error_flag": 5} for _ in range(5)]
        r = self.analyzer.analyze(bl, ofe)
        for name in ["partial_flag", "http_error_flag"]:
            self.assertEqual(r[name]["replication_rate"], 0.0)
            self.assertEqual(r[name]["status"], "not_repeated")

    def test_variance_change_detection(self) -> None:
        bl = [{"partial_flag": 5, "http_error_flag": 5} for _ in range(5)]
        ofe = [{"partial_flag": i, "http_error_flag": i} for i in range(5)]
        r = self.analyzer.analyze(bl, ofe)
        # baseline variance = 0, ofe variance > 0 → variance change = "increased"
        self.assertEqual(r["partial_flag"]["variance_change"], "increased")


class ConfidenceStabilityTests(unittest.TestCase):
    def test_analyze_returns_keys(self) -> None:
        a = ConfidenceStabilityAnalyzer()
        result = a.analyze(
            {"accuracy": [0.84, 0.86]},
            {"accuracy": [0.82, 0.83]},
        )
        self.assertIn("accuracy", result)
        self.assertIn("delta_correlation", result)

    def test_improvement_count(self) -> None:
        a = ConfidenceStabilityAnalyzer()
        result = a.analyze(
            {"calibration": [0.33, 0.34, 0.35]},
            {"calibration": [0.32, 0.33, 0.34]},
        )
        self.assertEqual(result["calibration"]["improvement_campaigns"], 3)
        self.assertEqual(result["calibration"]["regression_campaigns"], 0)


if __name__ == "__main__":
    unittest.main()
