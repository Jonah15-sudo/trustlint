import json
import os
import tempfile
import unittest
from pathlib import Path

from experiments.real_data_loader import load_real_tls_data


_VALID_ROW = {
    "case_id": "tls-001",
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


def _write_csv(path: str, rows: list) -> str:
    import csv
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_REQUIRED_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return path


class RealDataContractTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _path(self, name: str) -> str:
        return os.path.join(self.tmpdir, name)

    def test_valid_jsonl_accepted(self) -> None:
        path = _write_jsonl(self._path("test.jsonl"), [_VALID_ROW])
        result = load_real_tls_data(path)
        v = result["validation"]
        self.assertEqual(v["total"], 1)
        self.assertEqual(v["valid"], 1)
        self.assertEqual(v["skipped"], 0)
        self.assertEqual(len(result["valid_rows"]), 1)

    def test_valid_csv_accepted(self) -> None:
        path = _write_csv(self._path("test.csv"), [_VALID_ROW])
        result = load_real_tls_data(path)
        v = result["validation"]
        self.assertEqual(v["total"], 1)
        self.assertEqual(v["valid"], 1)
        self.assertEqual(v["skipped"], 0)

    def test_missing_field_rejected(self) -> None:
        row = dict(_VALID_ROW)
        del row["tls_valid"]
        path = _write_jsonl(self._path("missing.jsonl"), [row])
        result = load_real_tls_data(path)
        v = result["validation"]
        self.assertEqual(v["total"], 1)
        self.assertEqual(v["valid"], 0)
        self.assertEqual(v["skipped"], 1)

    def test_invalid_boolean_rejected(self) -> None:
        row = dict(_VALID_ROW)
        row["tls_valid"] = "not_a_bool"
        path = _write_jsonl(self._path("bad_bool.jsonl"), [row])
        result = load_real_tls_data(path)
        v = result["validation"]
        self.assertEqual(v["valid"], 0)
        self.assertEqual(v["skipped"], 1)

    def test_duplicate_case_id_counted(self) -> None:
        path = _write_jsonl(self._path("dupes.jsonl"), [_VALID_ROW, _VALID_ROW])
        result = load_real_tls_data(path)
        v = result["validation"]
        self.assertEqual(v["total"], 2)
        self.assertEqual(v["valid"], 1)
        self.assertEqual(v["skipped"], 1)
        self.assertIn("tls-001", v["duplicate_ids"])

    def test_invalid_timestamp_rejected(self) -> None:
        row = dict(_VALID_ROW)
        row["timestamp"] = "not-a-date"
        path = _write_jsonl(self._path("bad_ts.jsonl"), [row])
        result = load_real_tls_data(path)
        v = result["validation"]
        self.assertEqual(v["valid"], 0)
        self.assertEqual(v["skipped"], 1)

    def test_negative_latency_rejected(self) -> None:
        row = dict(_VALID_ROW)
        row["latency_ms"] = -1
        path = _write_jsonl(self._path("neg_lat.jsonl"), [row])
        result = load_real_tls_data(path)
        v = result["validation"]
        self.assertEqual(v["valid"], 0)

    def test_negative_bytes_received_rejected(self) -> None:
        row = dict(_VALID_ROW)
        row["bytes_received"] = -100
        path = _write_jsonl(self._path("neg_bytes.jsonl"), [row])
        result = load_real_tls_data(path)
        v = result["validation"]
        self.assertEqual(v["valid"], 0)

    def test_missing_label_rejected(self) -> None:
        row = dict(_VALID_ROW)
        del row["label"]
        path = _write_jsonl(self._path("no_label.jsonl"), [row])
        result = load_real_tls_data(path)
        v = result["validation"]
        self.assertEqual(v["valid"], 0)
        self.assertEqual(v["skipped"], 1)

    def test_validator_output_schema_stable(self) -> None:
        path = _write_jsonl(self._path("schema.jsonl"), [_VALID_ROW])
        result = load_real_tls_data(path)
        v = result["validation"]
        self.assertIn("total", v)
        self.assertIn("valid", v)
        self.assertIn("skipped", v)
        self.assertIn("duplicate_ids", v)
        self.assertIn("validation_errors", v)
        self.assertIn("positive_count", v)
        self.assertIn("negative_count", v)

    def test_no_spl_v7_import_in_validation(self) -> None:
        import experiments.real_data_loader
        import scripts.validate_real_tls_data
        for mod in [experiments.real_data_loader]:
            for name, obj in vars(mod).items():
                if hasattr(obj, "__module__"):
                    core_modules = ["spl_v7.causal", "spl_v7.dsl", "spl_v7.kafka_pipeline",
                                    "spl_v7.frontier", "spl_v7.verification", "spl_v7.dashboard"]
                    for core in core_modules:
                        self.assertFalse(
                            obj.__module__.startswith(core),
                            f"{mod.__name__} imports from {core} via {name}",
                        )

    def test_label_counting(self) -> None:
        row1 = dict(_VALID_ROW)
        row1["case_id"] = "a1"
        row1["label"] = True
        row2 = dict(_VALID_ROW)
        row2["case_id"] = "a2"
        row2["label"] = False
        row3 = dict(_VALID_ROW)
        row3["case_id"] = "a3"
        row3["label"] = True
        path = _write_jsonl(self._path("labels.jsonl"), [row1, row2, row3])
        result = load_real_tls_data(path)
        v = result["validation"]
        self.assertEqual(v["positive_count"], 2)
        self.assertEqual(v["negative_count"], 1)

    def test_empty_file(self) -> None:
        path = self._path("empty.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        result = load_real_tls_data(path)
        v = result["validation"]
        self.assertEqual(v["total"], 0)
        self.assertEqual(v["valid"], 0)

    def test_tls_expiry_too_large_rejected(self) -> None:
        row = dict(_VALID_ROW)
        row["tls_expiry_days"] = 999999
        path = _write_jsonl(self._path("expiry.jsonl"), [row])
        result = load_real_tls_data(path)
        v = result["validation"]
        self.assertEqual(v["valid"], 0)

    def test_real_tls_sample_file_is_parseable(self) -> None:
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "examples", "real_tls_sample.jsonl",
        )
        if os.path.isfile(sample_path):
            result = load_real_tls_data(sample_path)
            v = result["validation"]
            self.assertGreater(v["total"], 0)
            self.assertGreater(v["valid"], 0)
        else:
            self.skipTest("sample file not found")


if __name__ == "__main__":
    unittest.main()
