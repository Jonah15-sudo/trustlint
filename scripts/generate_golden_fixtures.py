#!/usr/bin/env python3
"""Generate CLI golden fixtures from current output format.

This script regenerates all golden fixture files to match the current
CLI output format. Run this after any changes to the output formatters.
"""

import json
import os
import sys
from unittest.mock import patch

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
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

SAMPLES_PATH = os.path.join(PROJECT_ROOT, "..", "datasets", "cli_golden_samples.json")
FIXTURES_DIR = os.path.join(PROJECT_ROOT, "..", "tests", "fixtures", "cli_golden")

import re
_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[\.,]\d+)?(?:[+-]\d{2}:\d{2})?Z?")
_PLACEHOLDER = "GENERATED_AT_PLACEHOLDER"


def _normalize_timestamps(text: str) -> str:
    return _TIMESTAMP_RE.sub(_PLACEHOLDER, text)


def _load_golden_samples():
    with open(SAMPLES_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    return dataset["samples"]


def _run_analyze(sample):
    mock_probe = sample["mocked_probe"]
    with patch("trustlint.analyzer.probe_domain", return_value=mock_probe):
        return analyze_domain(
            sample["domain"],
            profile=sample["profile"],
            timeout=10.0,
        )


def generate_fixtures():
    samples = _load_golden_samples()
    
    for sample in samples:
        sid = sample["id"]
        r = _run_analyze(sample)
        
        # Console fixture
        console_text = format_structured_text(r)
        console_path = os.path.join(FIXTURES_DIR, "console", f"{sid}.txt")
        with open(console_path, "w", encoding="utf-8") as f:
            f.write(console_text)
        print(f"Generated: {console_path}")
        
        # JSON fixture
        json_text = format_json_output([r], sample["profile"])
        json_text = _normalize_timestamps(json_text)
        json_path = os.path.join(FIXTURES_DIR, "json", f"{sid}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_text)
        print(f"Generated: {json_path}")
        
        # Markdown fixture
        md_text = format_markdown_output([r], sample["profile"])
        md_text = _normalize_timestamps(md_text)
        md_path = os.path.join(FIXTURES_DIR, "markdown", f"{sid}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_text)
        print(f"Generated: {md_path}")
    
    # Batch fixtures
    batch_results = [_run_analyze(s) for s in samples]
    batch_errors = []
    
    # Console batch summary
    batch_console = format_batch_summary(batch_results, batch_errors)
    batch_console_path = os.path.join(FIXTURES_DIR, "console", "_batch_summary.txt")
    with open(batch_console_path, "w", encoding="utf-8") as f:
        f.write(batch_console)
    print(f"Generated: {batch_console_path}")
    
    # JSON batch
    batch_json = format_json_output(batch_results, "balanced")
    batch_json = _normalize_timestamps(batch_json)
    batch_json_path = os.path.join(FIXTURES_DIR, "json", "_batch.json")
    with open(batch_json_path, "w", encoding="utf-8") as f:
        f.write(batch_json)
    print(f"Generated: {batch_json_path}")
    
    # Markdown batch
    batch_md = format_markdown_output(batch_results, "balanced")
    batch_md = _normalize_timestamps(batch_md)
    batch_md_path = os.path.join(FIXTURES_DIR, "markdown", "_batch.md")
    with open(batch_md_path, "w", encoding="utf-8") as f:
        f.write(batch_md)
    print(f"Generated: {batch_md_path}")
    
    print(f"\nGenerated {len(samples) * 3 + 3} fixture files")


if __name__ == "__main__":
    generate_fixtures()
