# TrustLint Demo Runbook

**Estimated time:** 5 minutes

## Prerequisites

- Python 3.10+
- TrustLint installed: `pip install -e .[dev]` or `uv sync --extra dev`

## 1. Fixture-Backed Demo (Offline, No Network)

This demo uses committed test fixtures. No external host is scanned.

```bash
# Run the offline fixture-backed analysis
uv run trustlint --json --quiet tests/fixtures/cli_golden/json/valid_tls.json
```

> **Note:** The fixture file is a static JSON document containing pre-recorded probe results.
> Sample output — fixture-backed; no external host was scanned.

### Expected Output

```json
{
  "metadata": { "tool": "trustlint", "version": "1.0.0", ... },
  "summary": { "total_domains": 1, "allow": 1, ... },
  "results": [
    {
      "domain": "example.com",
      "tls_probe": { "classification": "VALID_TLS", "tls_version": "TLSv1.3", ... },
      "final": { "decision": "ALLOW", "risk": "NONE", ... }
    }
  ]
}
```

**What this means:** The certificate is valid, the chain is complete, the protocol is modern (TLSv1.3), and no issues were found. The tool recommends no action.

## 2. Multi-Fixture Demo

Run multiple fixtures to show the range of findings:

```bash
uv run trustlint --json --quiet \
  tests/fixtures/cli_golden/json/valid_tls.json \
  tests/fixtures/cli_golden/json/expired_cert.json \
  tests/fixtures/cli_golden/json/deprecated_tls.json \
  tests/fixtures/cli_golden/json/untrusted_chain.json \
  tests/fixtures/cli_golden/json/self_signed_cert.json \
  tests/fixtures/cli_golden/json/incomplete_chain.json
```

### Expected Findings Summary

| Domain | Classification | Risk | Decision | Recommended Action |
|--------|---------------|------|----------|-------------------|
| example.com | VALID_TLS | NONE | ALLOW | No action required |
| expired.example.com | EXPIRED_CERT | HIGH | REVIEW | Renew or replace the certificate |
| old-tls.example.com | DEPRECATED_TLS_VERSION | HIGH | REVIEW | Disable TLS 1.0/1.1, require TLS 1.2+ |
| untrusted.example.com | UNTRUSTED_CHAIN | HIGH | REVIEW | Fix the certificate chain |
| self-signed.example.com | SELF_SIGNED_CERT | HIGH | REVIEW | Use a CA-issued certificate |
| incomplete.example.com | INCOMPLETE_CHAIN | HIGH | REVIEW | Install missing intermediate certificates |

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
