# TrustLint v1.0.0

**Production-grade TLS risk analysis CLI and library.**

Probe domains for TLS configuration weaknesses, classify results against a
structured risk taxonomy, and receive a deterministic **ALLOW / REVIEW / DENY**
decision with full reasoning and recommended actions.

---

## Features

- **20 TLS classifications** covering certificate validity, chain trust, protocol
  weaknesses, availability, and revocation.
- **3 security profiles** -- `conservative`, `balanced`, `strict` -- with a documented
  dispatch table (not a black box).
- **Concurrent probing** via `--workers N` (thread-pool, thread-safe).
- **OCSP + CRL revocation checking** using stdlib-only ASN.1 DER parsing.
- **Deprecated TLS detection** via a secondary TLS 1.1 probe.
- **3 output formats** -- console, JSON (versioned schema), Markdown.
- **Zero runtime dependencies** -- pure Python 3.10+ stdlib.
- **Clean exit codes** for CI/CD pipeline integration.
- **Health check** -- `--health` flag for Docker and deployment validation.
- **Structured logging** -- `--verbose`/`--quiet` flags with proper log levels.
- **Input validation** -- Domain name format validation.
- **Docker support** -- Container image with HEALTHCHECK.
- **702 tests** -- Comprehensive test suite (all passing).

---

## Installation

```bash
# From source
pip install -e .

# With Mozilla CA bundle (certifi)
pip install -e ".[ca-store]"

# For development (includes pytest)
pip install -e ".[dev]"
```

---

## Quick Start

```bash
# Single domain
trustlint example.com

# Batch from file, strict profile, JSON output
trustlint domains.txt --profile strict --json-out report.json

# List all registered TLS classifications
trustlint --list-classifications

# Version info
trustlint --version

# Health check
trustlint --health
```

---

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

---

## Security Profiles

| Classification | Severity | conservative | balanced | strict |
|---|---|---|---|---|
| REVOKED_CERT | CRITICAL | DENY | DENY | DENY |
| WRONG_HOST_CERT | CRITICAL | DENY | DENY | DENY |
| EXPIRED_CERT | HIGH | REVIEW | REVIEW | **DENY** |
| SELF_SIGNED_CERT | HIGH | REVIEW | REVIEW | **DENY** |
| UNTRUSTED_CHAIN | HIGH | REVIEW | REVIEW | **DENY** |
| DEPRECATED_TLS | HIGH | REVIEW | REVIEW | **DENY** |
| WILDCARD_CERTIFICATE | LOW | ALLOW | ALLOW | **REVIEW** |
| MISSING_OCSP_STAPLE | LOW | ALLOW | ALLOW | **REVIEW** |
| DNS_FAILURE | MEDIUM | REVIEW | REVIEW | REVIEW |
| VALID_TLS | NONE | **REVIEW** | ALLOW | **REVIEW** |

*Conservative* never auto-ALLOW; *balanced* allows clean VALID_TLS; *strict* denies all HIGH severity.

---

## Python API

```python
from trustlint import analyze, analyze_batch, get_version, get_classifications

# Single domain
result = analyze("example.com", profile="balanced")
print(result["final"]["decision"])  # "ALLOW"
print(result["final"]["risk"])      # "NONE"

# Batch analysis
results = analyze_batch(
    ["example.com", "expired.badssl.com"],
    profile="strict",
)

for r in results["results"]:
    print(f"{r['domain']}: {r['final']['decision']}")

# Version info
print(get_version())  # "1.0.0"

# List all classifications
print(get_classifications())
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All domains returned ALLOW |
| 1 | One or more domains returned REVIEW (no DENY) |
| 2 | One or more domains returned DENY |
| 3 | Fatal error (no domains, file not found, all errors) |

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest                          # all tests
pytest --tb=long -v             # verbose
pytest tests/test_risk_map.py   # one module
```

---

## Docker

```bash
# Build
docker build -t trustlint .

# Run
docker run --rm trustlint example.com

# Health check
docker run --rm trustlint --health
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-11 | RC-1 release |

---

## License

MIT
