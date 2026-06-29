# TLS Risk Analysis Report

**Generated:** 2026-06-03T18:43:09.438872+00:00Z
**Tool:** `TrustLint v1.0.0`
**Profile:** `balanced`
**CA Store:** `platform`
**Domains analyzed:** 12

> **Not production ready.** For local evidence gathering only.

---

## Executive Summary

| Metric | Value |
|---|---|
| Total domains | 12 |
| ALLOW | 1 |
| REVIEW | 10 |
| DENY | 1 |
| Fallback ALLOW (adapter policy) | 1 |
| Highest risk level | CRITICAL |
| Probe-limited | 4 |
| Probe errors | 1 |

---

## Domains Requiring Immediate Action

| Domain | Risk | Classification | Recommended Action |
|---|---|---|---|
| wronghost.example.com | CRITICAL | WRONG_HOST_CERT | Replace certificate with one matching the requested hostname. |

## Domains Requiring Manual Review

| Domain | Risk | Classification | Reason |
|---|---|---|---|
| expired.example.com | HIGH | EXPIRED_CERT | Security risk (balanced profile): RENEW_OR_DENY for EXPIRED_CERT |
| self-signed.example.com | HIGH | SELF_SIGNED_CERT | Security risk (balanced profile): REVIEW_OR_DENY for SELF_SIGNED_CERT |
| untrusted.example.com | HIGH | UNTRUSTED_CHAIN | Security risk (balanced profile): REVIEW_OR_DENY for UNTRUSTED_CHAIN |
| incomplete.example.com | HIGH | INCOMPLETE_CHAIN | Security risk (balanced profile): REVIEW_OR_DENY for INCOMPLETE_CHAIN |
| dnsfail.example.com | MEDIUM | DNS_FAILURE | Availability risk: REVIEW for DNS_FAILURE |
| timeout.example.com | MEDIUM | TIMEOUT | Availability risk: REVIEW for TIMEOUT |
| connrefused.example.com | MEDIUM | CONNECTION_ERROR | Availability risk: REVIEW for CONNECTION_ERROR |
| tlsfail.example.com | MEDIUM | TLS_HANDSHAKE_FAILURE | Ambiguous failure: INVESTIGATE for TLS_HANDSHAKE_FAILURE |
| old-tls.example.com | HIGH | DEPRECATED_TLS_VERSION | Security risk (balanced profile): MODERNIZE_OR_DENY for DEPRECATED_TLS_VERSION |
| unknown-error.example.com | LOW | UNKNOWN_SSL_ERROR | Ambiguous failure: INVESTIGATE for UNKNOWN_SSL_ERROR |

## Domains Allowed via Fallback (Not SPL Confidence)

The following domains were ALLOW'd by the adapter-based fallback policy because
SPL confidence was unavailable and the probe results were clean (balanced profile).

This is a deterministic adapter-policy decision, not an ML-based confidence score.

| Domain |
|---|
| example.com |

## Probe Limitations

| Domain | Limitation |
|---|---|
| expired.example.com | Certificate is expired according to the probe. |
| incomplete.example.com | Certificate chain is incomplete. |
| dnsfail.example.com | DNS resolution failed: Name or service not known |
| old-tls.example.com | Deprecated TLS version detected via secondary probe — server allows TLS 1.0 or 1.1 (primary negotiated TLSv1). |

---

## Full Per-Domain Results

| Domain | Classification | TLS | Adapter Risk | Severity | Decision | Recommended Action |
|---|---|---|---|---|---|---|
| example.com | VALID_TLS | TLSv1.3 | ACCEPTABLE_TLS | NONE | **ALLOW** | No action required. |
| expired.example.com | EXPIRED_CERT | TLSv1.2 | SECURITY_RISK | HIGH | **REVIEW** | Renew or replace the certificate immediately. |
| self-signed.example.com | SELF_SIGNED_CERT | TLSv1.2 | SECURITY_RISK | HIGH | **REVIEW** | Use a certificate issued by a trusted CA unless this is an internal-only system. |
| wronghost.example.com | WRONG_HOST_CERT | TLSv1.2 | SECURITY_RISK | CRITICAL | **DENY** | Replace certificate with one matching the requested hostname. |
| untrusted.example.com | UNTRUSTED_CHAIN | TLSv1.2 | SECURITY_RISK | HIGH | **REVIEW** | Fix the certificate chain — ensure all intermediate certificates are installed on the server. |
| incomplete.example.com | INCOMPLETE_CHAIN | TLSv1.2 | CHAIN_TRUST_FAILURE | HIGH | **REVIEW** | Install all missing intermediate certificates on the server. |
| dnsfail.example.com | DNS_FAILURE | - | AVAILABILITY_RISK | MEDIUM | **REVIEW** | Check DNS records and resolver availability for this domain. |
| timeout.example.com | TIMEOUT | - | AVAILABILITY_RISK | MEDIUM | **REVIEW** | Check network availability, firewall, or server responsiveness. The connection timed out. |
| connrefused.example.com | CONNECTION_ERROR | - | AVAILABILITY_RISK | MEDIUM | **REVIEW** | Check network availability and firewall rules for the target server. |
| tlsfail.example.com | TLS_HANDSHAKE_FAILURE | - | AMBIGUOUS_FAILURE | MEDIUM | **REVIEW** | Check TLS configuration and supported protocol/cipher settings on the server. |
| old-tls.example.com | DEPRECATED_TLS_VERSION | TLSv1 | DEPRECATED_PROTOCOL_RISK | HIGH | **REVIEW** | Disable deprecated TLS protocols (TLS 1.0/1.1) and require TLS 1.2+ or TLS 1.3. |
| unknown-error.example.com | UNKNOWN_SSL_ERROR | - | UNKNOWN_RISK | LOW | **REVIEW** | Investigate SSL error details manually — the specific cause could not be determined by automated probing. |

---

## Notes

1. SPL Core is not modified.
2. OFE remains HOLD_PENDING_REAL_DATA (observational only).
3. Adapter-only mode — no SPL pipeline was run.
4. Deprecated TLS detection is not guaranteed (OpenSSL negotiates highest version).
5. Probe limitations propagate through all decisions.
6. Fallback ALLOW (balanced profile) is a deterministic adapter-based policy, not SPL confidence.
7. No production readiness is claimed.

_Report generated by TrustLint v1.0.0._