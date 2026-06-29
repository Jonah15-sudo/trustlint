# TrustLint - CLI Usage

## Overview

TrustLint is a local CLI tool that analyzes TLS/domain risk through
the existing pipeline:

```
TLS Probe -> TLS Policy Adapter -> Decision Orchestrator -> structured report
```

## Installation

```bash
# From source
pip install -e .

# With Mozilla CA bundle (certifi)
pip install -e ".[ca-store]"
```

## Basic Usage

```bash
# Single domain
trustlint example.com

# With specific profile
trustlint example.com --profile strict

# Batch from file
trustlint domains.txt --profile strict --json-out report.json

# Markdown output
trustlint domains.txt --profile conservative --markdown-out report.md

# Quiet mode (batch summary only)
trustlint domains.txt --quiet --json-out report.json

# Custom timeout
trustlint example.com --timeout 30
```

## CLI Reference

```
trustlint [TARGET] [OPTIONS]

Input:
  TARGET                 Domain name or path to file with domains (one per line)

Profile:
  --profile PROFILE      conservative | balanced (default) | strict

Probe settings:
  --timeout SECONDS      Handshake timeout (default: 10.0)
  --ca-store STORE       platform (default) | certifi
  --workers N            Concurrent probe threads (default: 1)
  --rate-limit SECONDS   Min seconds between probes, sequential only (default: 0)

Output:
  --json-out FILE        Write JSON output to file
  --markdown-out FILE    Write Markdown report to file

Logging:
  --verbose              Enable verbose logging
  --quiet                Suppress non-essential output

Feature toggles:
  --spl-unsafe           [EXPERIMENTAL] Enable SPL Core observation mode

Utility:
  --health               Run health check and exit
  --list-classifications Print all 20 TLS classifications with risk mapping and exit
  --version              Print version and exit
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All domains returned ALLOW |
| 1 | One or more domains returned REVIEW (no DENY) |
| 2 | One or more DENY |
| 3 | Fatal error (no domains, file not found, all errors) |
| 4 | Invalid arguments |

## JSON Output Structure

```json
{
  "metadata": {
    "tool": "trustlint",
    "version": "1.0.0",
    "profile": "balanced",
    "generated_at": "2026-01-01T00:00:00Z"
  },
  "summary": {
    "total_domains": 3,
    "allow": 1,
    "review": 1,
    "deny": 1
  },
  "results": [...]
}
```
