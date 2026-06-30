"""Fixture-backed end-to-end CLI smoke test.

This test verifies that the CLI produces correct output by comparing
against golden fixtures. It uses mocked probe results to avoid
network calls.

All tests use the existing golden fixture files as the expected contract.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from typing import Any, Dict, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.spl_tls_analyze import (
    analyze_domain,
    format_structured_text,
    format_json_output,
    format_markdown_output,
    main,
)

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


class TestCLIEndToEndSmoke(unittest.TestCase):
    """End-to-end CLI smoke test using golden fixtures.

    These tests verify the complete CLI pipeline from domain analysis
    to output formatting, using mocked probe results.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = _load_golden_samples()

    def test_console_output_matches_golden(self) -> None:
        """Console output must match golden fixture for each sample."""
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
                f"Console output mismatch for {sid}",
            )

    def test_json_output_matches_golden(self) -> None:
        """JSON output must match golden fixture for each sample."""
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
                f"JSON output mismatch for {sid}",
            )

    def test_markdown_output_matches_golden(self) -> None:
        """Markdown output must match golden fixture for each sample."""
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
                f"Markdown output mismatch for {sid}",
            )

    def test_json_schema_is_valid(self) -> None:
        """JSON output must be valid JSON with required fields."""
        for sample in self.samples:
            sid = sample["id"]
            r = _run_analyze(sample)
            json_str = format_json_output([r], sample["profile"])
            parsed = json.loads(json_str)
            self.assertEqual(parsed["metadata"]["tool"], "trustlint", sid)
            self.assertEqual(parsed["metadata"]["production_ready"], False, sid)
            self.assertEqual(parsed["metadata"]["scope"], "local-only", sid)
            self.assertIn("results", parsed, sid)
            self.assertEqual(len(parsed["results"]), 1, sid)

    def test_main_end_to_end_with_mock(self) -> None:
        """main() must produce correct exit code with mocked probe."""
        sample = self.samples[0]
        mock_probe = sample["mocked_probe"]
        with patch("trustlint.analyzer.probe_domain", return_value=mock_probe):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                tmp = f.name
            try:
                exit_code = main([sample["domain"], "--json-out", tmp, "--quiet"])
                self.assertEqual(exit_code, sample["expected"]["exit_code"])
                with open(tmp, "r", encoding="utf-8") as f:
                    parsed = json.load(f)
                self.assertEqual(parsed["metadata"]["tool"], "trustlint")
            finally:
                os.unlink(tmp)


if __name__ == "__main__":
    unittest.main()
