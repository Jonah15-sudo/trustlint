# TrustLint Demo Runbook

**Estimated time:** 5 minutes

## Prerequisites

- Python 3.10+
- TrustLint installed: `pip install -e .[dev]` or `uv sync --extra dev`

## 1. Fixture-Backed Verification (Offline, No Network)

This step runs the deterministic fixture-backed end-to-end test path. Probe results are mocked. No external host is scanned. It proves the analysis/output contract, not a live TLS connection.

```bash
uv run pytest tests/test_cli_e2e_smoke.py -q
```

> **Note:** Sample output — fixture-backed; no external host was scanned.

### What This Proves

- The fixture-backed smoke suite verifies the committed sample classifications and their JSON, Markdown, and console output contracts.
- The output contract is stable and deterministic.

## 2. Fixture Inspection

You can inspect the recorded fixture output to see what the tool produces for each TLS classification. These are stored sample outputs — inspecting them does not execute a scan.

### JSON Fixtures

```bash
# View the valid TLS fixture
cat tests/fixtures/cli_golden/json/valid_tls.json

# View the expired certificate fixture
cat tests/fixtures/cli_golden/json/expired_cert.json

# View all JSON fixtures
ls tests/fixtures/cli_golden/json/
```

### Markdown Fixtures

```bash
# View the valid TLS fixture in Markdown format
cat tests/fixtures/cli_golden/markdown/valid_tls.md
```

### Console Fixtures

```bash
# View the valid TLS fixture in console format
cat tests/fixtures/cli_golden/console/valid_tls.txt
```

### Expected Findings Across Fixtures

| Fixture | Classification | Risk | Decision | Recommended Action |
|---------|---------------|------|----------|-------------------|
| valid_tls | VALID_TLS | NONE | ALLOW | No action required |
| expired_cert | EXPIRED_CERT | HIGH | REVIEW | Renew or replace the certificate |
| deprecated_tls | DEPRECATED_TLS_VERSION | HIGH | REVIEW | Disable TLS 1.0/1.1, require TLS 1.2+ |
| untrusted_chain | UNTRUSTED_CHAIN | HIGH | REVIEW | Fix the certificate chain |
| self_signed_cert | SELF_SIGNED_CERT | HIGH | REVIEW | Use a CA-issued certificate |
| incomplete_chain | INCOMPLETE_CHAIN | HIGH | REVIEW | Install missing intermediate certificates |

## 3. Authorized Live Demo (Requires Permission)

**Only run against domains you own or have written permission to assess.**

```bash
# Single domain
uv run trustlint your-domain.example.com

# With verbose output
uv run trustlint --verbose your-domain.example.com

# JSON output
uv run trustlint --json your-domain.example.com

# Markdown output
uv run trustlint --markdown your-domain.example.com

# Multiple domains
uv run trustlint domain1.example.com domain2.example.com
```

### CLI Flags Reference

| Flag | Description |
|------|-------------|
| `--json` | Output results as JSON |
| `--markdown` | Output results as Markdown |
| `--quiet, -q` | Suppress progress output |
| `--verbose, -v` | Enable verbose logging |
| `--profile {balanced,conservative,strict}` | Decision operating profile |
| `--ca-store {platform,certifi}` | CA trust store to use |
| `--timeout TIMEOUT` | Connection timeout in seconds |
| `--workers WORKERS` | Number of concurrent workers |
| `--output OUTPUT, -o` | Write output to file |
| `--list-classifications` | List all classification types |

## 4. Understanding the Output

### Certificate Validity
- **VALID_TLS:** Certificate is valid, chain is complete, not expired.
- **EXPIRED_CERT:** Certificate has expired. Renew immediately.
- **SELF_SIGNED_CERT:** Certificate is self-signed and not trusted by default.

### Hostname / Chain Issues
- **WRONG_HOST_CERT:** Certificate does not match the hostname.
- **UNTRUSTED_CHAIN:** Root CA is not in the trust store.
- **INCOMPLETE_CHAIN:** Server did not send intermediate certificates.

### Protocol / Cipher Findings
- **DEPRECATED_TLS_VERSION:** Server negotiated TLS 1.0 or 1.1.
- **WEAK_CIPHER_SUITE:** Server uses a weak cipher (e.g., RC4).
- **TLS_COMPRESSION_ENABLED:** TLS compression is enabled (CRIME attack risk).

### OCSP Evidence
- **OCSP stapling status** is reported when available.
- If OCSP is not performed, the tool notes this as informational.

### Recommended Next Action
Each finding includes a `recommended_action` field with specific remediation steps.

## 5. Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `uv sync --extra dev` or `pip install -e .[dev]` |
| Connection timeout | Increase `--timeout` value or check network |
| DNS failure | Verify the domain exists and resolves |
| `permission denied` on private IPs | Use `--allow-private-targets` (use with caution) |
| No OCSP data | Not all servers support OCSP stapling; this is informational |

## Important Notes

- An unavailable or inconclusive result is NOT a confirmed vulnerability.
- OCSP stapling is not universally deployed; absence does not indicate a defect.
- TrustLint is a screening tool, not a penetration test or compliance certification.
- Always obtain explicit authorization before scanning domains you do not own.
