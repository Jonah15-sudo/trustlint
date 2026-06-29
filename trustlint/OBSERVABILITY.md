# Observability Guide

This document describes how TrustLint reports its behavior through logging, structured output, exit codes, and error codes.

---

## Logging

TrustLint uses Python's built-in `logging` module. Log output is sent to `stderr` by default.

### Log Levels

| Level | Flag | Use Case |
|-------|------|----------|
| `WARNING` | `-v` | Unexpected but non-fatal conditions (e.g., self-signed cert detected) |
| `DEBUG` | `-vv` | Detailed diagnostic output (connection details, certificate fields) |

### Configuration

```bash
# Normal operation (errors only to stderr)
trustlint --url example.com

# Verbose output
trustlint -v --url example.com

# Debug output
trustlint -vv --url example.com
```

Log messages are not included in structured JSON output unless `--log-in-json` is specified.

### Log Format

Default text format:

```
[%(levelname)s] %(name)s: %(message)s
```

JSON format (when `--log-in-json` is enabled):

```json
{"level": "WARNING", "logger": "trustlint.scanner", "message": "Certificate expires in 5 days"}
```

---

## Structured Output Formats

TrustLint supports two output modes:

### Human-Readable (default)

```bash
trustlint --url example.com
```

Outputs a formatted table suitable for terminal display.

### JSON Output

```bash
trustlint --url example.com --output json
```

Outputs a JSON object to `stdout`. The schema is:

```json
{
  "target": "example.com:443",
  "scan_time": "2026-01-15T10:30:00Z",
  "certificates": [
    {
      "subject": "CN=example.com",
      "issuer": "CN=R3, O=Let's Encrypt",
      "not_before": "2025-12-01T00:00:00Z",
      "not_after": "2026-03-01T00:00:00Z",
      "serial": "03:AB:...",
      "san": ["example.com", "www.example.com"],
      "key_type": "RSA",
      "key_size": 2048,
      "signature_algorithm": "sha256RSA",
      "self_signed": false,
      "chain_valid": true,
      "trusted": true
    }
  ],
  "protocols": {
    "tls_1_3": true,
    "tls_1_2": true,
    "tls_1_1": false,
    "tls_1_0": false,
    "ssl_3_0": false
  },
  "cipher_suites": [
    {
      "name": "TLS_AES_256_GCM_SHA384",
      "protocol": "TLSv1.3",
      "strength": "strong"
    }
  ],
  "policy_violations": [],
  "warnings": [
    {
      "code": "W2001",
      "message": "Certificate expires within 30 days",
      "severity": "warning"
    }
  ],
  "exit_code": 0
}
```

---

## Exit Codes

TrustLint uses process exit codes to indicate scan results:

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | OK | No issues found. Target meets all checked policies. |
| `1` | ISSUES_FOUND | One or more policy violations or warnings detected. |
| `2` | ERROR | Runtime error (connection failed, invalid input, file not found). |
| `3` | PARTIAL | Scan completed but some checks could not be performed. |

### Using Exit Codes in Scripts

```bash
# Fail CI if any issues are found
trustlint --url example.com --output json --exit-on-issues
if [ $? -eq 1 ]; then
  echo "Policy violations detected"
  exit 1
fi
```

The `--exit-on-issues` flag makes TrustLint exit with code `1` if any warnings or violations exist, even if no errors occurred.

---

## Error Code System

TrustLint uses a structured error code system for programmatic consumption. Error codes follow the pattern `E{NNNN}` or `W{NNNN}`.

### Error Code Ranges

| Range | Category |
|-------|----------|
| `E1001`-`E1999` | Connection and network errors |
| `E2001`-`E2999` | Certificate parsing errors |
| `E3001`-`E3999` | Protocol and cipher suite errors |
| `E4001`-`E4999` | Policy evaluation errors |
| `E5001`-`E5999` | Input and argument errors |
| `E9001`-`E9999` | Internal/unexpected errors |
| `W1001`-`W9999` | Warnings (non-fatal) |

### Error Code Reference

| Code | Severity | Message |
|------|----------|---------|
| `E1001` | Error | Connection timed out |
| `E1002` | Error | DNS resolution failed |
| `E1003` | Error | Connection refused |
| `E1004` | Error | TLS handshake failed |
| `E2001` | Error | Invalid certificate format |
| `E2002` | Error | Certificate decoding failed |
| `E2003` | Error | Certificate chain incomplete |
| `E2004` | Error | Certificate has been revoked (CRL/OCSP) |
| `E3001` | Error | No supported cipher suites |
| `E3002` | Error | Protocol version not supported |
| `E4001` | Error | Policy rule evaluation failed |
| `E5001` | Error | Invalid command-line arguments |
| `E5002` | Error | Input file not found |
| `E5003` | Error | Input file not readable |
| `E9001` | Error | Unexpected internal error |
| `W1001` | Warning | Certificate expires within 30 days |
| `W1002` | Warning | Certificate expires within 7 days |
| `W2001` | Warning | Self-signed certificate detected |
| `W3001` | Warning | Deprecated protocol version enabled |
| `W3002` | Warning | Weak cipher suite detected |
| `W4001` | Warning | Policy rule triggered |

### Using Error Codes

Error codes are included in JSON output under `warnings[].code` and in the `exit_code` field. In human-readable output, they appear as `[E1001]` prefixes.

```bash
# Filter specific errors in scripts
trustlint --url example.com --output json | jq '.warnings[] | select(.code == "W1001")'
```

---

## Metrics (Future)

TrustLint does not currently export Prometheus/OpenTelemetry metrics. If observability instrumentation is added in the future, it will be opt-in and documented here.
