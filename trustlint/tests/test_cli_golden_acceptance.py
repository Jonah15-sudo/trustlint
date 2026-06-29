"""Golden sample acceptance tests for TrustLint CLI.

Golden samples freeze the current CLI behavior. Any change to expected output
requires a review of the golden samples.

No live network calls - all probe results are mocked from the golden dataset.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unittest
from unittest.mock import patch, MagicMock
from typing import Any, Dict, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from scripts.spl_tls_analyze import (
        analyze_domain,
        format_structured_text,
        format_json_output,
        format_markdown_output,
        format_batch_summary,
        compute_summary,
    )
    _HAS_SPL_TLS_ANALYZE = True
except ImportError:
    _HAS_SPL_TLS_ANALYZE = False

SAMPLES_PATH = os.path.join(PROJECT_ROOT, "datasets", "cli_golden_samples.json")
FIXTURES_DIR = os.path.join(PROJECT_ROOT, "tests", "fixtures", "cli_golden")

_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[\.,]\d+)?(?:[+-]\d{2}:\d{2})?Z?")
_PLACEHOLDER = "GENERATED_AT_PLACEHOLDER"


def _normalize_timestamps(text: str) -> str:
    return _TIMESTAMP_RE.sub(_PLACEHOLDER, text)


def _load_golden_samples() -> List[Dict[str, Any]]:
    with open(SAMPLES_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    return dataset["samples"]


def _run_analyze(sample: Dict[str, Any]) -> Dict[str, Any]:
    mock_probe = sample["mocked_probe"]
    with patch("trustlint.analyzer.probe_domain", return_value=mock_probe):
        return analyze_domain(
            sample["domain"],
            profile=sample["profile"],
            timeout=10.0,
        )


class TestGoldenFixtureSnapshots(unittest.TestCase):
    """Compare full output against golden fixture files.

    Timestamps in JSON and Markdown are normalized before comparison.
    Console text has no dynamic content.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = _load_golden_samples()

    def test_console_output_matches_fixtures(self) -> None:
        for sample in self.samples:
            sid = sample["id"]
            r = _run_analyze(sample)
            actual = format_structured_text(r)
            fixture_path = os.path.join(FIXTURES_DIR, "console", f"{sid}.txt")
            self.assertTrue(os.path.exists(fixture_path), f"Missing fixture: {fixture_path}")
            with open(fixture_path, "r", encoding="utf-8") as f:
                expected = f.read()
            self.assertEqual(
                actual, expected,
                f"Console output mismatch for {sid}. "
                f"Run the fixture generator to update snapshots.",
            )

    def test_json_output_matches_fixtures(self) -> None:
        for sample in self.samples:
            sid = sample["id"]
            r = _run_analyze(sample)
            actual = format_json_output([r], sample["profile"])
            actual = _normalize_timestamps(actual)
            fixture_path = os.path.join(FIXTURES_DIR, "json", f"{sid}.json")
            self.assertTrue(os.path.exists(fixture_path), f"Missing fixture: {fixture_path}")
            with open(fixture_path, "r", encoding="utf-8") as f:
                expected = f.read()
            expected = _normalize_timestamps(expected)
            self.assertEqual(
                actual, expected,
                f"JSON output mismatch for {sid}. "
                f"Run the fixture generator to update snapshots.",
            )

    def test_markdown_output_matches_fixtures(self) -> None:
        for sample in self.samples:
            sid = sample["id"]
            r = _run_analyze(sample)
            actual = format_markdown_output([r], sample["profile"])
            actual = _normalize_timestamps(actual)
            fixture_path = os.path.join(FIXTURES_DIR, "markdown", f"{sid}.md")
            self.assertTrue(os.path.exists(fixture_path), f"Missing fixture: {fixture_path}")
            with open(fixture_path, "r", encoding="utf-8") as f:
                expected = f.read()
            expected = _normalize_timestamps(expected)
            self.assertEqual(
                actual, expected,
                f"Markdown output mismatch for {sid}. "
                f"Run the fixture generator to update snapshots.",
            )


class TestGoldenConsoleSections(unittest.TestCase):
    """Verify all 6 required sections appear in console output."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = _load_golden_samples()

    def test_all_six_console_sections_present(self) -> None:
        for sample in self.samples:
            sid = sample["id"]
            r = _run_analyze(sample)
            text = format_structured_text(r)
            sections = ["[TLS Probe]", "[Policy Adapter]", "[SPL]",
                        "[Decision Reasoning]", "[Recommended Action]"]
            for sec in sections:
                self.assertIn(sec, text, f"Missing section '{sec}' in {sid}")

    def test_limitations_section_only_when_expected(self) -> None:
        for sample in self.samples:
            sid = sample["id"]
            r = _run_analyze(sample)
            text = format_structured_text(r)
            has_limitations = sample["expected"].get("limitation_substring") is not None
            if has_limitations:
                self.assertIn("[Limitations]", text,
                              f"Expected [Limitations] section in {sid}")
            else:
                self.assertNotIn("[Limitations]", text,
                                 f"Unexpected [Limitations] section in {sid}")


class TestGoldenJsonSchema(unittest.TestCase):
    """Verify JSON output schema for golden samples."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = _load_golden_samples()

    def test_json_metadata_fields(self) -> None:
        for sample in self.samples:
            sid = sample["id"]
            r = _run_analyze(sample)
            json_str = format_json_output([r], sample["profile"])
            parsed = json.loads(json_str)
            self.assertEqual(parsed["metadata"]["tool"], "trustlint", sid)
            self.assertEqual(parsed["metadata"]["production_ready"], False, sid)
            self.assertEqual(parsed["metadata"]["scope"], "local-only", sid)
            self.assertEqual(parsed["metadata"]["profile"], sample["profile"], sid)

    def test_json_has_summary_and_results(self) -> None:
        for sample in self.samples:
            sid = sample["id"]
            r = _run_analyze(sample)
            json_str = format_json_output([r], sample["profile"])
            parsed = json.loads(json_str)
            self.assertIn("summary", parsed, sid)
            self.assertIn("results", parsed, sid)
            self.assertEqual(len(parsed["results"]), 1, sid)
            self.assertEqual(parsed["results"][0]["domain"], sample["domain"], sid)


class TestGoldenExitCodes(unittest.TestCase):
    """Verify exit code contract for each golden sample."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = _load_golden_samples()

    def test_exit_code_matches_expected(self) -> None:
        from scripts.spl_tls_analyze import compute_exit_code
        for sample in self.samples:
            sid = sample["id"]
            r = _run_analyze(sample)
            code = compute_exit_code([r])
            expected = sample["expected"]["exit_code"]
            self.assertEqual(
                code, expected,
                f"{sid}: expected exit code {expected}, got {code}",
            )


class TestGoldenRecommendedActions(unittest.TestCase):
    """Verify recommended actions contain expected substrings."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = _load_golden_samples()

    def test_recommended_action_substring(self) -> None:
        for sample in self.samples:
            sid = sample["id"]
            r = _run_analyze(sample)
            action = r["final"]["recommended_action"]
            expected_sub = sample["expected"]["recommended_action_substring"]
            self.assertIn(expected_sub, action,
                          f"{sid}: expected '{expected_sub}' in recommended action, got '{action}'")


class TestGoldenLimitations(unittest.TestCase):
    """Verify limitation text when expected."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = _load_golden_samples()

    def test_limitation_substring_when_expected(self) -> None:
        for sample in self.samples:
            sid = sample["id"]
            r = _run_analyze(sample)
            expected_sub = sample["expected"].get("limitation_substring")
            limitations = r["final"]["limitations"]
            if expected_sub is not None:
                self.assertTrue(len(limitations) > 0,
                                f"{sid}: expected limitation '{expected_sub}' but none found")
                found = any(expected_sub in lim for lim in limitations)
                self.assertTrue(found,
                                f"{sid}: expected '{expected_sub}' in limitations, got {limitations}")
            else:
                self.assertEqual(len(limitations), 0,
                                 f"{sid}: expected no limitations, got {limitations}")


class TestGoldenProfilePreservation(unittest.TestCase):
    """Verify profile name is preserved in output."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = _load_golden_samples()

    def test_profile_in_result(self) -> None:
        for sample in self.samples:
            sid = sample["id"]
            r = _run_analyze(sample)
            self.assertEqual(r["profile"], sample["profile"], sid)


class TestGoldenOfeIsolation(unittest.TestCase):
    """Verify OFE is never observed in CLI output."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = _load_golden_samples()

    def test_ofe_not_observed(self) -> None:
        for sample in self.samples:
            sid = sample["id"]
            r = _run_analyze(sample)
            self.assertEqual(r["ofe_observed"], False,
                             f"{sid}: ofe_observed should be False")


class TestGoldenBatchSummary(unittest.TestCase):
    """Verify batch summary over all 12 golden samples."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = _load_golden_samples()
        cls.results = []
        for sample in cls.samples:
            r = _run_analyze(sample)
            cls.results.append(r)
        cls.summary = compute_summary(cls.results)
        cls.batch_text = format_batch_summary(cls.results)

    def test_total_count(self) -> None:
        self.assertEqual(self.summary["total_domains"], 12)

    def test_batch_allow_count(self) -> None:
        self.assertEqual(self.summary["allow"], 1)

    def test_batch_review_count(self) -> None:
        self.assertEqual(self.summary["review"], 10)

    def test_batch_deny_count(self) -> None:
        self.assertEqual(self.summary["deny"], 1)

    def test_batch_highest_risk(self) -> None:
        self.assertEqual(self.summary["highest_risk"], "CRITICAL")

    def test_batch_fallback_count(self) -> None:
        self.assertEqual(self.summary["fallback"], 1)

    def test_batch_probe_limited_count(self) -> None:
        self.assertEqual(self.summary["probe_limited"], 4)

    def test_batch_probe_errors(self) -> None:
        self.assertEqual(self.summary["probe_errors"], 1)

    def test_batch_text_has_immediate_action_section(self) -> None:
        self.assertIn("Immediate Action", self.batch_text)

    def test_batch_text_has_review_section(self) -> None:
        self.assertIn("Manual Review", self.batch_text)

    def test_batch_text_has_limitations_section(self) -> None:
        self.assertIn("Probe Limitations", self.batch_text)


class TestGoldenBatchSnapshot(unittest.TestCase):
    """Compare full batch output against golden snapshot files."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = _load_golden_samples()
        cls.results = []
        for sample in cls.samples:
            r = _run_analyze(sample)
            cls.results.append(r)

    def test_batch_console_snapshot(self) -> None:
        actual = format_batch_summary(self.results)
        fixture_path = os.path.join(FIXTURES_DIR, "console", "_batch_summary.txt")
        self.assertTrue(os.path.exists(fixture_path))
        with open(fixture_path, "r", encoding="utf-8") as f:
            expected = f.read()
        self.assertEqual(actual, expected, "Batch console snapshot mismatch")

    def test_batch_json_snapshot(self) -> None:
        actual = format_json_output(self.results, "balanced")
        actual = _normalize_timestamps(actual)
        fixture_path = os.path.join(FIXTURES_DIR, "json", "_batch.json")
        self.assertTrue(os.path.exists(fixture_path))
        with open(fixture_path, "r", encoding="utf-8") as f:
            expected = f.read()
        expected = _normalize_timestamps(expected)
        self.assertEqual(actual, expected, "Batch JSON snapshot mismatch")

    def test_batch_markdown_snapshot(self) -> None:
        actual = format_markdown_output(self.results, "balanced")
        actual = _normalize_timestamps(actual)
        fixture_path = os.path.join(FIXTURES_DIR, "markdown", "_batch.md")
        self.assertTrue(os.path.exists(fixture_path))
        with open(fixture_path, "r", encoding="utf-8") as f:
            expected = f.read()
        expected = _normalize_timestamps(expected)
        self.assertEqual(actual, expected, "Batch Markdown snapshot mismatch")


if __name__ == "__main__":
    unittest.main()
