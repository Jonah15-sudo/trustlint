# Sample TLS Security Review — Technical Preview

> **This is a sample report using fixture-backed data. No external host was scanned.**
> The domains and findings below are illustrative and do not represent a real assessment.

## Executive Summary

TrustLint analyzed six TLS configurations across certificate validity, trust chain integrity, protocol versions, and cipher suites. Five high-severity findings were identified requiring remediation. One configuration passed all checks.

| Metric | Count |
|--------|-------|
| Endpoints analyzed | 6 |
| ALLOW (no issues) | 1 |
| REVIEW (action required) | 5 |
| HIGH severity | 5 |
| CRITICAL severity | 0 |

## Findings by Severity

### HIGH

#### 1. Expired Certificate

- **Domain:** expired.example.com
- **Classification:** EXPIRED_CERT
- **Evidence:** Certificate expiry days: -1 (expired). TLS version: TLSv1.2. Chain: complete.
- **Recommended Action:** Renew or replace the certificate immediately.

#### 2. Deprecated TLS Version

- **Domain:** old-tls.example.com
- **Classification:** DEPRECATED_TLS_VERSION
- **Evidence:** Server negotiated TLS 1.0. Deprecated TLS version detected via secondary probe.
- **Recommended Action:** Disable deprecated TLS protocols (TLS 1.0/1.1) and require TLS 1.2+ or TLS 1.3.

#### 3. Untrusted Certificate Chain

- **Domain:** untrusted.example.com
- **Classification:** UNTRUSTED_CHAIN
- **Evidence:** Certificate chain is complete but root CA is not trusted. TLS version: TLSv1.2.
- **Recommended Action:** Fix the certificate chain — ensure all intermediate certificates are installed on the server and the root CA is in the trust store.

#### 4. Self-Signed Certificate

- **Domain:** self-signed.example.com
- **Classification:** SELF_SIGNED_CERT
- **Evidence:** Certificate is self-signed and not trusted. TLS version: TLSv1.2. Chain: complete.
- **Recommended Action:** Use a certificate issued by a trusted CA unless this is an internal-only system.

#### 5. Incomplete Certificate Chain

- **Domain:** incomplete.example.com
- **Classification:** INCOMPLETE_CHAIN
- **Evidence:** Server did not send intermediate certificate. Chain complete: false. TLS version: TLSv1.2.
- **Recommended Action:** Install all missing intermediate certificates on the server.

### INFORMATIONAL

#### 6. Valid TLS Configuration

- **Domain:** example.com
- **Classification:** VALID_TLS
- **Evidence:** TLSv1.3. Certificate valid for 89 days. Chain complete. No OCSP data available.
- **Recommended Action:** No action required.

## Limitations

- This report uses fixture-backed data, not live scan results.
- OCSP stapling status was not available in the sample data.
- TrustLint is a screening tool, not a penetration test or compliance certification.
- Results are point-in-time and do not guarantee security.
- No exploitation or intrusion testing was performed.
