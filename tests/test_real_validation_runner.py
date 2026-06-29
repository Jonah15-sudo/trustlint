import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

from experiments.real_validation_runner import RealValidationRunner, _build_results_json, _build_summary_md, _build_promotion_assessment_md
from experiments.real_data_loader import load_real_tls_data


_VALID_ROW = {
    "case_id": "tls-000001",
    "timestamp": "2026-01-15T08:30:00Z",
    "tls_valid": True,
    "tls_expiry_days": 30,
    "http_status": "ok",
    "partial_response": False,
    "timeout": False,
    "hsts_present": True,
    "csp_present": True,
    "latency_ms": 120,
    "bytes_received": 4096,
    "label": False,
}

_REQUIRED_FIELDS = [
    "case_id", "timestamp", "tls_valid", "tls_expiry_days", "http_status",
    "partial_response", "timeout", "hsts_present", "csp_present",
    "latency_ms", "bytes_received", "label",
]


def _write_jsonl(path: str, rows: list) -> str:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return path


def _generate_valid_rows(count: int, positive_pct: float = 20.0) -> list:
    rows = []
    n_pos = max(1, int(count * positive_pct / 100))
    for i in range(count):
        row = dict(_VALID_ROW)
        row["case_id"] = f"tls-{i:06d}"
        row["label"] = i < n_pos
        row["tls_valid"] = not row["label"]
        row["latency_ms"] = 1800 if row["label"] else 90
        row["bytes_received"] = 256 if row["label"] else 4096
        row["hsts_present"] = not row["label"]
        row["csp_present"] = not row["label"] or i % 7 == 0
        row["http_status"] = "timeout" if row["label"] and i % 11 == 0 else "ok"
        row["partial_response"] = row["label"]
        row["timeout"] = row["label"]
        rows.append(row)
    return rows


def _make_campaign(accuracy: float, error_rate: float, calib_error: float,
                   collapse_rate: float, total_weak: int, idx: int = 0) -> dict:
    return {
        "campaign_index": idx,
        "training_items": 5000,
        "ofe_signals": 15,
        "baseline": {
            "accuracy": {"accuracy": accuracy, "total_processed": 25, "total_predicted": 25, "correct": int(accuracy * 25), "sample_size": 25},
            "error_rate": {"total": 25, "errors": int(error_rate * 25), "error_rate": error_rate},
            "calibration": {"sample_size": 25, "mean_confidence": 0.85, "accuracy": accuracy, "calibration_error": calib_error, "ece": calib_error * 0.6},
            "collapse": {"total_sequences": 5, "collapse_count": int(collapse_rate * 5), "collapse_rate": collapse_rate, "mean_drop_magnitude": 0.1},
            "total_weaknesses": total_weak,
            "weakness_frequency": [
                {"weakness": "partial_flag", "frequency": 2, "percent_of_total": 16.7, "sample_size": total_weak},
                {"weakness": "http_error_flag", "frequency": 1, "percent_of_total": 8.3, "sample_size": total_weak},
            ],
            "weakness_counts": {"partial_flag": 2, "http_error_flag": 1, "hsts_missing": 0},
            "difficulty_distribution": {},
            "capability_boundary": {"fraction_below": 0.2, "points_below_threshold": 5, "points_above_threshold": 20},
        },
        "ofe": {
            "accuracy": {"accuracy": accuracy + 0.01, "total_processed": 25, "total_predicted": 25, "correct": int((accuracy + 0.01) * 25), "sample_size": 25},
            "error_rate": {"total": 25, "errors": int(error_rate * 20), "error_rate": error_rate - 0.005},
            "calibration": {"sample_size": 25, "mean_confidence": 0.86, "accuracy": accuracy + 0.01, "calibration_error": calib_error - 0.01, "ece": (calib_error - 0.01) * 0.6},
            "collapse": {"total_sequences": 5, "collapse_count": int((collapse_rate - 0.02) * 5), "collapse_rate": collapse_rate - 0.02, "mean_drop_magnitude": 0.08},
            "total_weaknesses": total_weak - 2,
            "weakness_frequency": [
                {"weakness": "partial_flag", "frequency": 1, "percent_of_total": 10.0, "sample_size": total_weak - 2},
            ],
            "weakness_counts": {"partial_flag": 1, "http_error_flag": 0, "hsts_missing": 0},
            "difficulty_distribution": {},
            "capability_boundary": {"fraction_below": 0.18, "points_below_threshold": 4, "points_above_threshold": 21},
        },
        "comparison": {
            "accuracy": {"A": accuracy, "B": accuracy + 0.01, "absolute_difference": 0.01, "percentage_difference": 1.18, "direction": "improvement"},
            "calibration_error": {"A": calib_error, "B": calib_error - 0.01, "absolute_difference": -0.01, "percentage_difference": -20.0, "direction": "improvement"},
            "error_rate": {"A": error_rate, "B": error_rate - 0.005, "absolute_difference": -0.005, "percentage_difference": -25.0, "direction": "improvement"},
            "collapse_rate": {"A": collapse_rate, "B": collapse_rate - 0.02, "absolute_difference": -0.02, "percentage_difference": -20.0, "direction": "improvement"},
            "total_weaknesses": {"A": float(total_weak), "B": float(total_weak - 2), "absolute_difference": -2.0, "percentage_difference": -16.67, "direction": "improvement"},
            "weakness_level": [],
            "difficulty_distribution": {},
            "capability_boundary": {"a_fraction_below": 0.2, "b_fraction_below": 0.18, "delta_fraction_below": -0.02},
        },
    }


class RealValidationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        self._clean_output_dir()

    def _path(self, name: str) -> str:
        return os.path.join(self.tmpdir, name)

    def test_runner_refuses_missing_dataset(self) -> None:
        runner = RealValidationRunner(campaign_count=1)
        with self.assertRaises(FileNotFoundError):
            runner.run(self._path("nonexistent.jsonl"))

    def test_runner_refuses_empty_file(self) -> None:
        path = self._path("empty.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        runner = RealValidationRunner(campaign_count=1)
        with self.assertRaises(ValueError) as cm:
            runner.run(path)
        self.assertIn("zero valid rows", str(cm.exception).lower())

    def test_runner_refuses_too_few_rows(self) -> None:
        rows = _generate_valid_rows(100)
        path = _write_jsonl(self._path("small.jsonl"), rows)
        runner = RealValidationRunner(campaign_count=1)
        with self.assertRaises(ValueError) as cm:
            runner.run(path)
        self.assertIn("minimum 5000", str(cm.exception))

    def test_runner_refuses_invalid_rows(self) -> None:
        rows = _generate_valid_rows(10)
        rows[0]["tls_valid"] = "bad_value"
        path = _write_jsonl(self._path("invalid.jsonl"), rows)
        runner = RealValidationRunner(campaign_count=1)
        with self.assertRaises(ValueError) as cm:
            runner.run(path)
        self.assertIn("invalid", str(cm.exception).lower())

    def test_runner_refuses_low_positive_ratio(self) -> None:
        rows = _generate_valid_rows(5000, positive_pct=1.0)
        path = _write_jsonl(self._path("low_pos.jsonl"), rows)
        runner = RealValidationRunner(campaign_count=1)
        with self.assertRaises(ValueError) as cm:
            runner.run(path)
        self.assertIn("positive label ratio", str(cm.exception).lower())

    def test_runner_refuses_sample_fixture(self) -> None:
        rows = _generate_valid_rows(5000, positive_pct=20.0)
        path = self._path("real_tls_sample.jsonl")
        _write_jsonl(path, rows)
        runner = RealValidationRunner(campaign_count=1)
        with self.assertRaises(ValueError) as cm:
            runner.run(path)
        self.assertIn("sample fixture", str(cm.exception).lower())

    def test_runner_accepts_valid_dataset_structural(self) -> None:
        import time
        rows = _generate_valid_rows(5000, positive_pct=20.0)
        path = _write_jsonl(self._path("structural.jsonl"), rows)
        runner = RealValidationRunner(campaign_count=1)
        t0 = time.time()
        results = runner.run(path)
        elapsed = time.time() - t0
        self.assertLess(elapsed, 600.0,
                        f"Runner took {elapsed:.1f}s which exceeds 600s limit")
        self.assertIn("metadata", results)
        self.assertIn("dataset", results)
        self.assertIn("aggregated", results)
        self.assertIn("campaigns", results)
        self.assertEqual(len(results["campaigns"]), 1)

        found = 0
        import glob as _glob
        for d in _glob.glob("reports/real_data_validation_*"):
            for fname in ["real_data_validation_results.json",
                           "real_data_validation_summary.md",
                           "real_data_promotion_assessment.md"]:
                fpath = os.path.join(d, fname)
                if os.path.isfile(fpath):
                    found += 1
        self.assertGreaterEqual(found, 3, f"Missing output files in reports/real_data_validation_*/")

        self.assertEqual(results["metadata"]["runner"], "RealValidationRunner")
        self.assertIn("frontier_sample", results["metadata"])
        self.assertEqual(results["metadata"]["frontier_sample"]["max_frontier_rows"], 200)

        note = results["metadata"]["note"]
        self.assertIn("HOLD_PENDING_REAL_DATA", note)
        self.assertIn("No OFE signal was promoted", note)

    def test_runner_verbose_mode(self) -> None:
        rows = _generate_valid_rows(100)
        path = _write_jsonl(self._path("small.jsonl"), rows)
        runner = RealValidationRunner(campaign_count=1, verbose=True)
        with self.assertRaises(ValueError):
            runner.run(path)

    def test_runner_does_not_modify_spl_v7(self) -> None:
        spl_v7_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "spl_v7",
        )
        before = set()
        for root, dirs, files in os.walk(spl_v7_dir):
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    before.add((path, os.path.getmtime(path)))

        rows = _generate_valid_rows(5000, positive_pct=20.0)
        path = _write_jsonl(self._path("splcheck.jsonl"), rows)
        runner = RealValidationRunner(campaign_count=1)
        results = runner.run(path)
        self.assertIn("frontier_sample", results["metadata"])

        after = set()
        for root, dirs, files in os.walk(spl_v7_dir):
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    after.add((path, os.path.getmtime(path)))

        self.assertEqual(before, after, "spl_v7/ was modified")

    def test_aggregation_correct_numeric_values(self) -> None:
        c1 = _make_campaign(accuracy=0.85, error_rate=0.02, calib_error=0.05, collapse_rate=0.10, total_weak=12, idx=0)
        c2 = _make_campaign(accuracy=0.87, error_rate=0.015, calib_error=0.04, collapse_rate=0.08, total_weak=10, idx=1)
        result = RealValidationRunner._aggregate_campaigns([c1, c2])

        bm = result["baseline_mean"]
        om = result["ofe_mean"]

        self.assertAlmostEqual(bm["accuracy"], 0.86, places=4)
        self.assertAlmostEqual(bm["error_rate"], 0.0175, places=4)
        self.assertAlmostEqual(bm["calibration_error"], 0.045, places=4)
        self.assertAlmostEqual(bm["collapse_rate"], 0.09, places=4)
        self.assertAlmostEqual(bm["total_weaknesses"], 11.0, places=1)

        self.assertAlmostEqual(om["accuracy"], 0.87, places=4)
        self.assertAlmostEqual(om["error_rate"], 0.0125, places=4)
        self.assertAlmostEqual(om["calibration_error"], 0.035, places=4)
        self.assertAlmostEqual(om["collapse_rate"], 0.07, places=4)
        self.assertAlmostEqual(om["total_weaknesses"], 9.0, places=1)

    def test_aggregation_regime_summary(self) -> None:
        c1 = _make_campaign(accuracy=0.85, error_rate=0.02, calib_error=0.05, collapse_rate=0.10, total_weak=12, idx=0)
        c2 = _make_campaign(accuracy=0.87, error_rate=0.015, calib_error=0.04, collapse_rate=0.08, total_weak=10, idx=1)
        result = RealValidationRunner._aggregate_campaigns([c1, c2])

        regimes = {r["metric"]: r for r in result["regime_summary"]}

        self.assertIn("accuracy", regimes)
        self.assertGreater(regimes["accuracy"]["mean_delta"], 0)
        self.assertEqual(regimes["accuracy"]["improvement_count"], 2)

        self.assertIn("calibration_error", regimes)
        self.assertLess(regimes["calibration_error"]["mean_delta"], 0)
        self.assertEqual(regimes["calibration_error"]["improvement_count"], 2)

    def test_aggregation_single_campaign(self) -> None:
        c = _make_campaign(accuracy=0.85, error_rate=0.02, calib_error=0.05, collapse_rate=0.10, total_weak=12, idx=0)
        result = RealValidationRunner._aggregate_campaigns([c])

        self.assertEqual(result["campaign_count"], 1)
        self.assertAlmostEqual(result["baseline_mean"]["accuracy"], 0.85, places=4)
        self.assertAlmostEqual(result["ofe_mean"]["accuracy"], 0.86, places=4)
        self.assertEqual(result["regime_summary"][0]["improvement_rate"], 100.0)

    def test_aggregation_weakness_frequency(self) -> None:
        c = _make_campaign(accuracy=0.85, error_rate=0.02, calib_error=0.05, collapse_rate=0.10, total_weak=12, idx=0)
        result = RealValidationRunner._aggregate_campaigns([c])

        bfreq = result["baseline_mean"]["weakness_frequency"]
        names = [f["weakness"] for f in bfreq]
        self.assertIn("partial_flag", names)
        self.assertIn("http_error_flag", names)

    def test_output_schema_stable(self) -> None:
        aggregated = {
            "campaign_count": 2,
            "baseline_mean": {
                "accuracy": 0.85,
                "error_rate": 0.02,
                "calibration_error": 0.05,
                "collapse_rate": 0.1,
                "total_weaknesses": 12.0,
                "weakness_frequency": [],
            },
            "ofe_mean": {
                "accuracy": 0.86,
                "error_rate": 0.015,
                "calibration_error": 0.04,
                "collapse_rate": 0.08,
                "total_weaknesses": 10.0,
                "weakness_frequency": [],
            },
            "regime_summary": [
                {"metric": "accuracy", "mean_delta": 0.01, "improvement_rate": 50.0},
                {"metric": "calibration_error", "mean_delta": -0.01, "improvement_rate": 50.0},
            ],
            "overall": "INCONCLUSIVE",
        }

        validation = {"total": 5000, "valid": 5000, "skipped": 0, "positive_count": 1000, "negative_count": 4000}
        campaigns = [{"campaign_index": 0, "training_items": 5000, "ofe_signals": 15, "baseline": {}, "ofe": {}, "comparison": {}}]

        results = _build_results_json("/fake/path.jsonl", validation, aggregated, campaigns, frontier_sample_size=200)
        self.assertIn("metadata", results)
        self.assertIn("dataset", results)
        self.assertIn("aggregated", results)
        self.assertIn("campaigns", results)
        self.assertEqual(results["metadata"]["runner"], "RealValidationRunner")
        self.assertEqual(results["dataset"]["valid_rows"], 5000)

        summary_md = _build_summary_md("/fake/path.jsonl", validation, aggregated, total_rows=5000, frontier_sample_size=200)
        self.assertIn("Real Data Validation Summary", summary_md)
        self.assertIn("INCONCLUSIVE", summary_md)

        promotion_md = _build_promotion_assessment_md(aggregated)
        self.assertIn("HOLD_PENDING_REAL_DATA", promotion_md)
        self.assertIn("No signal was promoted by this runner", promotion_md)

    def test_no_promotion_from_sample_data(self) -> None:
        aggregated = {
            "campaign_count": 1,
            "baseline_mean": {
                "accuracy": 0.85,
                "error_rate": 0.02,
                "calibration_error": 0.05,
                "collapse_rate": 0.1,
                "total_weaknesses": 12.0,
                "weakness_frequency": [],
            },
            "ofe_mean": {
                "accuracy": 0.86,
                "error_rate": 0.015,
                "calibration_error": 0.04,
                "collapse_rate": 0.08,
                "total_weaknesses": 10.0,
                "weakness_frequency": [],
            },
            "regime_summary": [
                {"metric": "accuracy", "mean_delta": 0.01, "improvement_count": 1, "regression_count": 0, "unchanged_count": 0, "improvement_rate": 100.0},
                {"metric": "calibration_error", "mean_delta": -0.01, "improvement_count": 1, "regression_count": 0, "unchanged_count": 0, "improvement_rate": 100.0},
                {"metric": "error_rate", "mean_delta": -0.005, "improvement_count": 1, "regression_count": 0, "unchanged_count": 0, "improvement_rate": 100.0},
                {"metric": "collapse_rate", "mean_delta": -0.02, "improvement_count": 1, "regression_count": 0, "unchanged_count": 0, "improvement_rate": 100.0},
                {"metric": "total_weaknesses", "mean_delta": -2.0, "improvement_count": 1, "regression_count": 0, "unchanged_count": 0, "improvement_rate": 100.0},
            ],
            "overall": "CANDIDATE_FOR_PROMOTION",
        }

        promotion_md = _build_promotion_assessment_md(aggregated)
        self.assertIn("CANDIDATE_FOR_PROMOTION", promotion_md)
        self.assertIn("No signal was promoted by this runner", promotion_md)
        self.assertIn("ADVISORY", promotion_md)
        self.assertIn("Human review", promotion_md)

    def test_campaign_count_validates(self) -> None:
        with self.assertRaises(ValueError):
            RealValidationRunner(campaign_count=0)

    def test_runner_name_in_results(self) -> None:
        aggregated = {
            "campaign_count": 0,
            "baseline_mean": {"accuracy": 0, "error_rate": 0, "calibration_error": 0, "collapse_rate": 0, "total_weaknesses": 0, "weakness_frequency": []},
            "ofe_mean": {"accuracy": 0, "error_rate": 0, "calibration_error": 0, "collapse_rate": 0, "total_weaknesses": 0, "weakness_frequency": []},
            "regime_summary": [],
            "overall": "INCONCLUSIVE",
        }
        results = _build_results_json("/fake.jsonl", {"total": 0, "valid": 0, "skipped": 0, "positive_count": 0, "negative_count": 0}, aggregated, [], frontier_sample_size=0)
        self.assertEqual(results["metadata"]["runner"], "RealValidationRunner")
        self.assertIn("HOLD_PENDING_REAL_DATA", results["metadata"]["note"])

    def test_runner_can_run_twice_in_same_process(self) -> None:
        path_a = self._path("seq_a.jsonl")
        path_b = self._path("seq_b.jsonl")
        _write_jsonl(path_a, _generate_valid_rows(5000, positive_pct=20.0))
        _write_jsonl(path_b, _generate_valid_rows(5000, positive_pct=20.0))

        script = (
            "import sys, json, gc; "
            "sys.path.insert(0, '.'); "
            f"path_a = {json.dumps(path_a)}; "
            f"path_b = {json.dumps(path_b)}; "
            "from experiments.real_validation_runner import RealValidationRunner; "
            "r1 = RealValidationRunner(campaign_count=1); "
            "res1 = r1.run(path_a); "
            "gc.collect(); "
            "print('RUN1_DONE'); "
            "r2 = RealValidationRunner(campaign_count=1); "
            "res2 = r2.run(path_b); "
            "gc.collect(); "
            "print('RUN2_DONE'); "
            "out = {'r1': res1['aggregated']['overall'], 'r2': res2['aggregated']['overall']}; "
            "json.dump(out, sys.stdout)"
        )
        t0 = time.time()
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=180,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        elapsed = time.time() - t0

        if proc.returncode != 0:
            self.fail(
                f"Sequential run failed (exit={proc.returncode}, {elapsed:.1f}s):\n"
                f"stdout: {proc.stdout[:2000]}\n"
                f"stderr: {proc.stderr[:2000]}"
            )

        self.assertIn("RUN1_DONE", proc.stdout)
        self.assertIn("RUN2_DONE", proc.stdout)
        self.assertIn("NOT_READY_REGRESSION_DETECTED", proc.stdout)

        result = json.loads(proc.stdout[proc.stdout.index("{"):proc.stdout.rindex("}")+1])
        self.assertIn("r1", result)
        self.assertIn("r2", result)

    def _clean_output_dir(self):
        import glob as _glob
        for d in _glob.glob("reports/real_data_validation_*"):
            try:
                import shutil
                shutil.rmtree(d, ignore_errors=True)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
