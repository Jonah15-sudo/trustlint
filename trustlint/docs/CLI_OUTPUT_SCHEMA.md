# CLI Output Schema - TrustLint JSON

## Overview

The JSON output produced by `--json-out FILE` follows this schema.

## Top-Level Structure

```json
{
  "metadata": { ... },
  "summary": { ... },
  "results": [ ... ]
}
```

## Metadata Object

| Field | Type | Description |
|-------|------|-------------|
| `tool` | string | Always `"trustlint"` |
| `profile` | string | Operating profile used: `"conservative"`, `"balanced"`, or `"strict"` |
| `generated_at` | string | ISO 8601 UTC timestamp |
| `scope` | string | Always `"local-only"` |

### Example

```json
{
  "metadata": {
    "tool": "trustlint",
    "profile": "balanced",
    "generated_at": "2026-06-01T12:00:00Z",
    "scope": "local-only"
  }
}
```

## Summary Object

| Field | Type | Description |
|-------|------|-------------|
| `total_domains` | integer | Number of domains analyzed |
| `allow` | integer | Count of ALLOW decisions |
| `review` | integer | Count of REVIEW decisions |
| `deny` | integer | Count of DENY decisions |
| `fallback` | integer | Count of ALLOW decisions via adapter fallback |
| `probe_limited` | integer | Count of domains with probe limitations |
| `probe_errors` | integer | Count of domains with probe errors |
| `highest_risk` | string | Highest risk level across all domains |

## Result Object

Each result contains:

| Field | Type | Description |
|-------|------|-------------|
| `domain` | string | Domain analyzed |
| `profile` | string | Profile used |
| `ca_store` | string | CA store used |
| `tls_probe` | object | TLS probe results |
| `policy_adapter` | object | Policy adapter results |
| `final` | object | Final decision |

### TLS Probe Object

| Field | Type | Description |
|-------|------|-------------|
| `classification` | string | TLS classification (see `--list-classifications`) |
| `resolved_ip` | string | Resolved IP address |
| `port` | integer | Port scanned |
| `timestamp` | string | ISO 8601 UTC timestamp |
| `is_probe_limited` | boolean | Whether probe had limitations |
| `warnings` | array | List of probe warnings |
| `tls` | object | Detailed TLS information |

### Final Decision Object

| Field | Type | Description |
|-------|------|-------------|
| `decision` | string | `ALLOW`, `REVIEW`, or `DENY` |
| `risk` | string | Risk level: `NONE`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `source` | string | Decision source |
| `fallback_used` | boolean | Whether fallback was used |
| `primary_reason` | string | Primary reason for decision |
| `recommended_action` | string | Recommended action |

## Example Result

```json
{
  "domain": "example.com",
  "profile": "balanced",
  "ca_store": "platform",
  "tls_probe": {
    "classification": "VALID_TLS",
    "resolved_ip": "93.184.216.34",
    "port": 443,
    "timestamp": "2026-06-01T12:00:00Z",
    "is_probe_limited": false,
    "warnings": [],
    "tls": {
      "tls_version": "TLSv1.3",
      "cipher_name": "TLS_AES_256_GCM_SHA384",
      "cert_expiry_days": 74,
      "cert_is_expired": false,
      "cert_is_self_signed": false,
      "cert_chain_length": 3,
      "cert_chain_complete": true,
      "wildcard_cert": false,
      "handshake_ms": 124.3
    }
  },
  "policy_adapter": {
    "risk_category": "ACCEPTABLE_TLS",
    "severity": "NONE",
    "failure_family": "NONE",
    "policy_reason": "TLS handshake succeeded with a valid, trusted certificate chain.",
    "action_hint": "NONE"
  },
  "final": {
    "decision": "ALLOW",
    "risk": "NONE",
    "source": "ADAPTER_FALLBACK",
    "fallback_used": true,
    "primary_reason": "VALID_TLS allowed by balanced profile",
    "recommended_action": "No action required."
  }
}
```
