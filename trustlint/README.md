# TrustLint

[![CI](https://github.com/trustlint/trustlint/actions/workflows/ci.yml/badge.svg)](https://github.com/trustlint/trustlint/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A command-line tool and Python library for analyzing TLS/SSL configurations of domains and assessing risk based on certificate properties, protocol support, and revocation status.

---

## What TrustLint Does

TrustLint connects to a target domain over TLS, inspects the negotiated connection, and classifies the result against a taxonomy of 20 TLS risk categories. It then applies a configurable security profile to produce a deterministic **ALLOW**, **REVIEW**, or **DENY** decision.

**Capabilities:**

- Probe TLS handshake parameters (certificate, chain, protocol version)
- Detect expired, revoked, self-signed, and wrong-host certificates
- Check OCSP stapling and CRL revocation status
- Identify deprecated TLS versions (1.0, 1.1)
- Classify results into 20 risk categories with severity levels
- Apply one of three security profiles: `conservative`, `balanced`, or `strict`
- Output results in console, JSON, or Markdown format
- Analyze single domains or batch from file

## What TrustLint Does Not Do

- It is **not** a vulnerability scanner or penetration testing tool
- It does **not** enumerate services, open ports, or perform network mapping
- It does **not** guarantee the absence of security issues
- It does **not** replace comprehensive TLS auditing tools
- It does **not** perform active exploitation or fuzzing

## Security Scope and Limitations

TrustLint operates from the perspective of an external observer performing a TLS handshake. It cannot inspect server-side configuration, internal certificate authorities, or application-layer security.

**Known limitations:**

- OCSP checking is best-effort; results depend on responder availability
- Deprecated TLS detection depends on the server's negotiation behavior
- No IPv6 support in the current TLS probing implementation
- Revocation status may be stale between CRL update intervals
- SPL Core integration is experimental and should not be relied upon for security decisions

---

## Installation

### From source

```bash
git clone https://github.com/trustlint/trustlint.git
cd trustlint
pip install -e .
```

### With Mozilla CA bundle

```bash
pip install -e ".[ca-store]"
```

### For development

```bash
pip install -e ".[dev]"
```

### From wheel

```bash
pip install trustlint-<version>-py3-none-any.whl
```

---

## CLI Usage

```bash
# Analyze a single domain
trustlint example.com

# Analyze multiple domains from a file
trustlint domains.txt --profile strict --json-out report.json

# List all TLS classifications
trustlint --list-classifications

# Run health check
trustlint --health

# Print version
trustlint --version
```

### CLI Reference

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

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All domains returned ALLOW |
| 1 | One or more domains returned REVIEW (no DENY) |
| 2 | One or more domains returned DENY |
| 3 | Fatal error (no domains, file not found, all errors) |

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
print(get_version())

# List all classifications
print(get_classifications())
```

---

## Security Profiles

TrustLint applies different decision thresholds based on the selected profile:

| Classification | Severity | conservative | balanced | strict |
|---|---|---|---|---|
| REVOKED_CERT | CRITICAL | DENY | DENY | DENY |
| WRONG_HOST_CERT | CRITICAL | DENY | DENY | DENY |
| EXPIRED_CERT | HIGH | REVIEW | REVIEW | DENY |
| SELF_SIGNED_CERT | HIGH | REVIEW | REVIEW | DENY |
| UNTRUSTED_CHAIN | HIGH | REVIEW | REVIEW | DENY |
| DEPRECATED_TLS | HIGH | REVIEW | REVIEW | DENY |
| WILDCARD_CERTIFICATE | LOW | ALLOW | ALLOW | REVIEW |
| MISSING_OCSP_STAPLE | LOW | ALLOW | ALLOW | REVIEW |
| DNS_FAILURE | MEDIUM | REVIEW | REVIEW | REVIEW |
| VALID_TLS | NONE | REVIEW | ALLOW | REVIEW |

- **conservative**: Never auto-allows; everything goes to REVIEW or DENY
- **balanced**: Allows clean VALID_TLS; reviews or denies based on severity
- **strict**: Denies all HIGH severity findings and above

---

## Configuration

TrustLint uses safe defaults. No configuration file is required for basic usage.

**Default behavior:**

- Timeout: 10 seconds per handshake
- Profile: `balanced`
- CA store: platform default
- Workers: 1 (sequential probing)
- Rate limiting: disabled

**Environment variables:**

- `TRUSTLINT_LOG_LEVEL` -- Override log level (DEBUG, INFO, WARNING, ERROR)

---

## Private Target Scanning

By default, TrustLint rejects connections to private, loopback, link-local, multicast, and reserved IP ranges. This prevents accidental scanning of internal infrastructure.

To scan private targets (authorized internal systems only):

```bash
trustlint internal.example.com --allow-private-targets
```

**Use this only on systems you own or are authorized to test.**

---

## OCSP Behavior

OCSP checking is performed on a best-effort basis:

- Results depend on the availability of the certificate's OCSP responder
- If the responder is unreachable, the OCSP status is reported as unknown
- OCSP stapling is detected when the server provides a stapled response
- CRL checking uses DER-encoded CRL data parsed with stdlib ASN.1

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

## Development

### Setup

```bash
git clone https://github.com/trustlint/trustlint.git
cd trustlint
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest                          # all tests
pytest --tb=long -v             # verbose output
pytest tests/test_risk_map.py   # single module
```

### Project Structure

```
trustlint/
├── trustlint/          # Main package
├── tests/              # Test suite
├── docs/               # Documentation
├── frontier/           # Experimental features
├── experiments/        # Research and validation
├── reports/            # Generated reports
├── pyproject.toml      # Project metadata
├── requirements.txt    # Dependencies
└── Dockerfile          # Container build
```

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design documentation including:

- Module structure and responsibilities
- Decision flow and risk classification
- TLS probing implementation
- Security controls and input validation

---

## Contributing

Contributions are welcome. Please read the existing code style and test patterns before submitting changes.

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

---

## Security Policy

See [SECURITY.md](SECURITY.md) for vulnerability reporting guidelines.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
