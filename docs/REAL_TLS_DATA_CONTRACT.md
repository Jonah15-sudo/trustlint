# Real TLS Data Contract

## Format

JSONL (preferred) or CSV with header row.

### JSONL

One JSON object per line. Keys match the field names below.

```json
{"case_id": "tls-001", "timestamp": "2026-01-15T08:30:00Z", "tls_valid": true, "tls_expiry_days": 30, "http_status": "ok", "partial_response": false, "timeout": false, "hsts_present": true, "csp_present": true, "latency_ms": 120, "bytes_received": 4096, "label": false}
{"case_id": "tls-002", "timestamp": "2026-01-15T08:30:01Z", "tls_valid": false, "tls_expiry_days": -5, "http_status": "timeout", "partial_response": true, "timeout": true, "hsts_present": false, "csp_present": false, "latency_ms": 3200, "bytes_received": 256, "label": true}
```

### CSV

```csv
case_id,timestamp,tls_valid,tls_expiry_days,http_status,partial_response,timeout,hsts_present,csp_present,latency_ms,bytes_received,label
tls-001,2026-01-15T08:30:00Z,true,30,ok,false,false,true,true,120,4096,false
tls-002,2026-01-15T08:30:01Z,false,-5,timeout,true,true,false,false,3200,256,true
```

---

## Schema

| Field | Type | Required | Description |
|---|---|---|---|
| `case_id` | string | yes | Unique identifier for the TLS case |
| `timestamp` | string (ISO-8601) | yes | When the TLS handshake or check occurred |
| `tls_valid` | boolean | yes | Whether the TLS certificate passed basic validation |
| `tls_expiry_days` | integer | yes | Days until certificate expiry (negative = expired) |
| `http_status` | string | yes | HTTP response status: `ok`, `timeout`, `error`, `redirect` |
| `partial_response` | boolean | yes | Whether the server returned a partial HTTP response |
| `timeout` | boolean | yes | Whether the connection timed out |
| `hsts_present` | boolean | yes | Whether the HSTS header was present |
| `csp_present` | boolean | yes | Whether the Content-Security-Policy header was present |
| `latency_ms` | integer | yes | Connection latency in milliseconds |
| `bytes_received` | integer | yes | Total bytes received |
| `label` | boolean | yes | Ground truth: `true` = risky, `false` = clean |

---

## Accepted Types

| Python type | JSON type | CSV representation |
|---|---|---|
| `str` | string | Quoted or unquoted string |
| `int` | number (integer) | Integer digits |
| `bool` | boolean | `true` / `false` (lowercase) |
| `float` | number | Decimal number when applicable |

---

## Missing-Value Behavior

| Scenario | Handling |
|---|---|
| Missing required field | Row is **skipped** and logged |
| Null/None in boolean field | Row is **skipped** |
| Null/None in integer field | Row is **skipped** |
| Null/None in string field | Row is **skipped** |
| Missing `label` | Row is **skipped** |
| Empty file | Error: no valid rows |

No default values are substituted. Silently dropping incomplete rows is not permitted — all skipped rows must be counted and reported.

---

## Invalid-Row Handling

| Condition | Action |
|---|---|
| Duplicate `case_id` | Keep first occurrence, log warning |
| Non-boolean in boolean field | Skip row, log warning |
| Non-integer in integer field | Skip row, log warning |
| Negative `latency_ms` | Skip row, log warning |
| Negative `bytes_received` | Skip row, log warning |
| `tls_expiry_days` > 36500 | Skip row, log warning |
| Unrecognized `http_status` | Accept as string, no validation |
| Invalid ISO-8601 timestamp | Skip row, log warning |

---

## Privacy and Security Constraints

1. **No PII.** The dataset must not contain personally identifiable information (names, email addresses, IP addresses, user IDs).
2. **No credentials.** TLS private keys, session tickets, or pre-shared keys must not appear in any field.
3. **No raw payloads.** HTTP response bodies must not be included.
4. **No source correlation.** Source identifiers must be opaque (e.g., `collector-a`, not hostnames or IPs).
5. **Data at rest.** The dataset file must be stored with restricted access (read-only for the analysis process).
6. **Data in transit.** If transferring the dataset, use TLS 1.3 or SSH.
7. **Retention.** Delete the dataset after validation completes unless retention is explicitly authorized.
