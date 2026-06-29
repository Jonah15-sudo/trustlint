# Release Notes — spl-tls-analyze v0.3.0b0 (superseded by v0.3.2b0)

**Date:** 2026-06-04  
**Status:** Pre-release (PEP 440 beta)

## What's New Since v0.2.0b0

### 5 New TLS Detection Categories

The deterministic probe now covers 20 total classifications, adding:

| Category | Severity | Detection Method |
|----------|:--------:|-----------------|
| `WEAK_CIPHER_SUITE` | HIGH | Cipher name pattern match (RC4/3DES/NULL/EXP/DES) |
| `STATIC_RSA_KEY_EXCHANGE` | MEDIUM | Cipher name pattern match (RSA without DHE/ECDHE) |
| `TLS_COMPRESSION_ENABLED` | MEDIUM | Post-handshake compression field check |
| `WILDCARD_CERTIFICATE` | LOW | SubjectAltName DNS prefix `*.` detection |
| `MISSING_OCSP_STAPLE` | LOW | OCSP staple absence detection |

### Policy & Orchestration Updates

- New `MEDIUM_SEVERITY_SECURITY_RISKS` list (STATIC_RSA_KEY_EXCHANGE, TLS_COMPRESSION_ENABLED) — Rule 2a: REVIEW for all profiles
- New `LOW_SEVERITY_SECURITY_RISKS` list (WILDCARD_CERTIFICATE, MISSING_OCSP_STAPLE) — Rule 2b: REVIEW for all profiles

### SPL Core Deprecation

SPL module is now explicitly deprecated as research-only:
- Import warning via `warnings.warn()` in `spl_v7/__init__.py`
- `--spl` flag renamed to `--spl-unsafe` with loud accuracy warning (28%)
- `experimental/EXPERIMENTAL_WARNING.md` documents research-only status
- `docs/SPL_VALIDATION_FINDINGS.md` summarizes all validation experiments

### Test Suite

597 tests (up from 520 in v0.2.0b0) — 77 new tests:
- 25 tests in `test_tls_probe.py`
- 20 tests in `test_tls_policy_adapter.py` (5 new classes)
- Updated `test_spl_tls_analyze.py` for `--spl-unsafe` flag

### Dogfood Validation

Full 47-domain batch scan against real public domains (see `docs/DOGFOOD_v0.3.md`):
- 0 crashes, 0 probe errors
- WILDCARD_CERTIFICATE and MISSING_OCSP_STAPLE confirmed in the wild
- WEAK_CIPHER_SUITE, STATIC_RSA_KEY_EXCHANGE, TLS_COMPRESSION_ENABLED confirmed extinct on modern internet
- Major finding: ALLOW count dropped to 0 due to new categories — mitigations documented

## Upgrade Notes

- `--spl` flag no longer exists. Use `--spl-unsafe` instead (with explicit warning acknowledgement).
- The `spl_v7` package still exists at the same import path but emits a `UserWarning` on import.
- All existing test imports and internal scripts continue to work unchanged.

## Known Limitations

1. WEAK_CIPHER_SUITE cannot be negotiated on Python 3.14 (RC4/NULL removed from default cipher list).
2. STATIC_RSA_KEY_EXCHANGE and TLS_COMPRESSION_ENABLED are extinct on the public internet.
3. MISSING_OCSP_STAPLE fires even when the certificate has no OCSP URL configured.
4. OCSP revocation checking is best-effort (revoked.badssl.com not detected).
5. Deprecated TLS detection is platform-dependent (OpenSSL negotiates highest version).
6. Single-IP probing only (first A record resolved).

## Validation

- **Tests:** 597 passed, 5 skipped, 0 failures
- **Dogfood:** 47 domains, 0 errors, 8 categories detected
- **Version consistency:** Verified across all key files
