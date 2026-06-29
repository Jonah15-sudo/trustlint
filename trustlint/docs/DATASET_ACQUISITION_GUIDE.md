# Dataset Acquisition Guide

## Required Schema

Each row must contain exactly these 12 fields:

| Field | Type | Description |
|---|---|---|
| `case_id` | string | Unique identifier |
| `timestamp` | string (ISO-8601) | When the TLS check occurred |
| `tls_valid` | boolean | TLS certificate passed basic validation |
| `tls_expiry_days` | integer | Days until certificate expiry (negative = expired) |
| `http_status` | string | `ok`, `timeout`, `error`, or `redirect` |
| `partial_response` | boolean | Server returned a partial HTTP response |
| `timeout` | boolean | Connection timed out |
| `hsts_present` | boolean | HSTS header was present |
| `csp_present` | boolean | Content-Security-Policy header was present |
| `latency_ms` | integer | Connection latency in milliseconds |
| `bytes_received` | integer | Total bytes received |
| `label` | boolean | Ground truth: `true` = risky, `false` = clean |

## Format

- **JSONL** (preferred): one JSON object per line, keys matching the field names above.
- **CSV**: header row with field names, one row per record.

## Minimum Requirements

| Requirement | Minimum |
|---|---|
| Total rows | 5,000 |
| Positive labels (risky) | 10% of total (≥500) |
| Invalid/skipped rows | 0 (all rows must pass contract validation) |

## Source Recommendations

1. **TLS monitoring platforms** (Cloudflare, Let's Encrypt, Shodan, Censys) — export connection logs with certificate metadata.
2. **Network telemetry** (Zeek/Bro logs, Suricata TLS events) — extract the required fields from `tls.log` or equivalent.
3. **Security scanners** (masscan, ZGrab, TLS-Scanner) — instrument scans to produce the schema above.

## Privacy & Sanitization Requirements

1. **No PII.** Remove names, email addresses, IP addresses, and user IDs.
2. **No credentials.** TLS private keys, session tickets, and pre-shared keys must not appear in any field.
3. **No raw payloads.** HTTP response bodies must not be included.
4. **Opaque source identifiers.** Use opaque labels (e.g., `collector-a`) instead of hostnames or IPs.
5. **Labels must be ground truth.** Do not derive labels from model output. Labels must be based on external verification (known-bad certificate, confirmed compromise, etc.).
6. **No label leakage.** Feature fields (`tls_valid`, `timeout`, `hsts_present`, etc.) must not be derived from the label.

## Validation

```bash
# Validate any dataset against the contract
python scripts/validate_real_tls_data.py path/to/dataset.jsonl

# Run the full validation pipeline
python -m experiments.real_validation_runner path/to/dataset.jsonl 1 --verbose

# Run 12 A/B campaigns for replication
python -m experiments.real_validation_runner path/to/dataset.jsonl 12
```

## CI Integration

Set the `REAL_TLS_DATASET` environment variable in your CI environment:

```bash
export REAL_TLS_DATASET=/path/to/real_tls_dataset.jsonl
```

When set, CI runs the full real-data validation pipeline. When unset, CI skips real-data validation and reports `HOLD_PENDING_REAL_DATA`.
