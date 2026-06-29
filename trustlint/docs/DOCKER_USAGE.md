# Docker Usage - TrustLint v1.0.0

## Overview

The Docker image packages the TrustLint CLI for reproducible local
execution. It runs the same code as the pip-installed package -- no web
server, no API, no open ports, no services.

**Not production ready.** For local evidence gathering only.

## Build

```bash
docker build -t trustlint .
```

The image uses `python:3.10-slim` (~120 MB base) and installs the package
with its stdlib-only dependencies.

## Run Single Domain

```bash
docker run --rm trustlint example.com
docker run --rm trustlint example.com --profile balanced
docker run --rm trustlint example.com --profile strict
docker run --rm trustlint example.com --verbose
```

The default profile is `balanced`.

## Run Batch from File

```bash
# Linux/macOS
docker run --rm -v "$(pwd)/datasets:/app/datasets" trustlint /app/datasets/dogfood_domains.txt

# Windows (PowerShell)
docker run --rm -v "${PWD}/datasets:/app/datasets" trustlint /app/datasets/dogfood_domains.txt
```

## Output to Host

```bash
# JSON output
docker run --rm -v "$(pwd)/reports:/app/reports" trustlint example.com --json-out /app/reports/result.json

# Markdown output
docker run --rm -v "$(pwd)/reports:/app/reports" trustlint example.com --markdown-out /app/reports/report.md
```

## Health Check

```bash
docker run --rm trustlint --health
```

## Network Host Mode

```bash
docker run --rm --network host trustlint example.com
```

## Notes

- No API or dashboard -- CLI only
- No persistent storage -- all output must be mounted out
- No root access -- runs as non-root user
- Health check built into image
