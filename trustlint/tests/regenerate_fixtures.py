"""Regenerate golden fixture files from current code output.

Run with: python -m tests.regenerate_fixtures
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List
from unittest.mock import patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.spl_tls_analyze import (
    analyze_domain,
    format_structured_text,
    format_json_output,
    format_markdown_output,
    format_batch_summary,
    compute_summary,
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


def main() -> None:
    samples = _load_golden_samples()

    # Generate per-sample fixtures
    for sample in samples:
        sid = sample["id"]
        r = _run_analyze(sample)

        # Console fixture
        console_path = os.path.join(FIXTURES_DIR, "console", f"{sid}.txt")
        with open(console_path, "w", encoding="utf-8") as f:
            f.write(format_structured_text(r))
        print(f"  Wrote {console_path}")

        # JSON fixture
        json_path = os.path.join(FIXTURES_DIR, "json", f"{sid}.json")
        json_str = format_json_output([r], [])
        json_str = _normalize_timestamps(json_str)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"  Wrote {json_path}")

        # Markdown fixture
        md_path = os.path.join(FIXTURES_DIR, "markdown", f"{sid}.md")
        md_str = format_markdown_output([r], [])
        md_str = _normalize_timestamps(md_str)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_str)
        print(f"  Wrote {md_path}")

    # Generate batch fixtures
    batch_results = []
    batch_errors = []
    for sample in samples:
        r = _run_analyze(sample)
        batch_results.append(r)

    # Batch console
    batch_console_path = os.path.join(FIXTURES_DIR, "console", "_batch_summary.txt")
    batch_text = format_batch_summary(batch_results, batch_errors)
    with open(batch_console_path, "w", encoding="utf-8") as f:
        f.write(batch_text)
    print(f"  Wrote {batch_console_path}")

    # Batch JSON
    batch_json_path = os.path.join(FIXTURES_DIR, "json", "_batch.json")
    batch_json_str = format_json_output(batch_results, batch_errors)
    batch_json_str = _normalize_timestamps(batch_json_str)
    with open(batch_json_path, "w", encoding="utf-8") as f:
        f.write(batch_json_str)
    print(f"  Wrote {batch_json_path}")

    # Batch Markdown
    batch_md_path = os.path.join(FIXTURES_DIR, "markdown", "_batch.md")
    batch_md_str = format_markdown_output(batch_results, batch_errors)
    batch_md_str = _normalize_timestamps(batch_md_str)
    with open(batch_md_path, "w", encoding="utf-8") as f:
        f.write(batch_md_str)
    print(f"  Wrote {batch_md_path}")

    print(f"\nRegenerated {len(samples)} sample fixtures + batch fixtures.")


if __name__ == "__main__":
    main()
