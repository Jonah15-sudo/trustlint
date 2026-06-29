# TrustLint - CLI Examples

## Basic Usage

```bash
# Single domain
trustlint example.com

# With specific profile
trustlint example.com --profile strict
```

## Output Formats

```bash
# JSON output
trustlint example.com --json-out report.json

# Markdown output
trustlint example.com --markdown-out report.md
```

## Batch Processing

```bash
# Analyze multiple domains from file
trustlint domains.txt --profile balanced

# Quiet mode (summary only)
trustlint domains.txt --quiet --json-out report.json
```

## Specific Classifications

```bash
# Expired certificate
trustlint expired.example.com

# Self-signed certificate
trustlint self-signed.example.com

# DNS failure
trustlint dnsfail.example.com
```

## Advanced Options

```bash
# Custom timeout
trustlint example.com --timeout 30

# Verbose output
trustlint example.com --verbose

# List all classifications
trustlint --list-classifications

# Health check
trustlint --health
```

## Python API

```python
from trustlint import analyze, analyze_batch

# Single domain
result = analyze("example.com", profile="balanced")
print(result["final"]["decision"])  # "ALLOW"

# Batch analysis
results = analyze_batch(
    ["example.com", "expired.badssl.com"],
    profile="strict",
)

for r in results["results"]:
    print(f"{r['domain']}: {r['final']['decision']}")
```
