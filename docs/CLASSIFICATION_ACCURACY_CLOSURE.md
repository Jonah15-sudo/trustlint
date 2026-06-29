# Phase 24: Classification Accuracy Closure

## Objective
Resolve two classification gaps identified during Phase 22/23:
1. **SHA-1 badssl domains** → classified as `UNKNOWN_SSL_ERROR` (catch-all) instead of a meaningful category
2. **UNTRUSTED_CHAIN subtypes** → no decomposition into root cause (missing intermediate, enterprise CA, government CA, untrusted root)

## Changes Made

| File | Change |
|------|--------|
| `tls_policy_adapter/schema.py` | Added `WEAK_SIGNATURE_ALGORITHM` to `TLSClassification` literal, `RISK_MAP`, `_POLICY_REASONS`, `_ACTION_HINTS` |
| `scripts/run_local_tls_validation.py` | Added `"too weak"`/`"digest algorithm"` match in `_classify_ssl_error()`; added `_determine_chain_subtype()` with CERT_NONE fallback probe |
| `scripts/spl_tls_analyze.py` | Added `WEAK_SIGNATURE_ALGORITHM` to `_RECOMMENDED_ACTIONS` |
| `scripts/run_real_tls_spl_decision_validation.py` | Added `WEAK_SIGNATURE_ALGORITHM` to `CLASSIFICATION_TO_POLICY`, security set, ambiguous set |
| `tests/test_spl_decision_validation.py` | Added `WEAK_SIGNATURE_ALGORITHM` to `ALL_CLASSIFICATIONS` |

## Classification Logic

### WEAK_SIGNATURE_ALGORITHM (new)
- **Trigger**: OpenSSL error `"CA signature digest algorithm too weak"`
- **Risk**: SECURITY_RISK
- **Severity**: HIGH
- **Failure family**: PROTOCOL_WEAKNESS
- **Previously**: `UNKNOWN_SSL_ERROR` (catch-all → UNKNOWN_RISK, LOW)

### UNTRUSTED_CHAIN subtypes (new, metadata only)
- **Top-level classification unchanged**: `UNTRUSTED_CHAIN` → SECURITY_RISK, HIGH
- **Subtypes exposed in `info["chain_subtype"]`**:
  - `missing_intermediate`: chain length < 2 (server cert only)
  - `enterprise_ca`: issuer contains internal/enterprise keywords (e.g., "Corp", "Internal", "Domain Controller")
  - `government_ca`: issuer contains government keywords (e.g., "Government", "Gov", "State", "Federal")
  - `untrusted_root`: chain present but root not in CA store (default)

## Verification Results

### Test Suite
```
530 passed, 42 subtests passed in 55.26s
```
No regressions. All existing classification mappings remain intact.

### SHA-1 badssl Probe Results
| Domain | Before (Phase 22) | After (Phase 24) |
|--------|-------------------|------------------|
| `sha1-2016.badssl.com` | `UNKNOWN_SSL_ERROR` | `WEAK_SIGNATURE_ALGORITHM` |
| `sha1-2017.badssl.com` | `UNKNOWN_SSL_ERROR` | `WEAK_SIGNATURE_ALGORITHM` |
| `sha1-intermediate.badssl.com` | `UNKNOWN_SSL_ERROR` | `WEAK_SIGNATURE_ALGORITHM` |

### Error Message Classification Accuracy
| Error message | Classification | Result |
|---------------|---------------|--------|
| `CA signature digest algorithm too weak` | `WEAK_SIGNATURE_ALGORITHM` | ✅ |
| `unable to get local issuer certificate` | `UNTRUSTED_CHAIN` | ✅ |
| `certificate has expired` | `EXPIRED_CERT` | ✅ |
| `Hostname mismatch` | `WRONG_HOST_CERT` | ✅ |

## Limitations

### Known
- **UNTRUSTED_CHAIN subtype detection** requires a second `CERT_NONE` SSL connection, which adds latency (~1s per domain) and may fail if the server has strict SNI requirements
- **Subtype classification** uses basic keyword matching on issuer CN — enterprise CA keywords may not cover all internal CA naming conventions (e.g., `"Company CA"` without explicit `"Corp"`/`"Internal"` tokens)
- **WEAK_SIGNATURE_ALGORITHM** currently only matches `"too weak"` + `"digest algorithm"` — other SSL library versions may produce different error strings

### Not Addressed (Out of Scope)
- CRL/OCSP revocation checking
- Certificate transparency log verification
- Additional protocol weakness detection (e.g., RC4, 3DES cipher suites)
- SHA-1 leaf certificate detection (current OpenSSL only reports CA-level SHA-1; leaf SHA-1 certificates may produce different errors)

## Future Recommendations
1. Expand UNTRUSTED_CHAIN subtype keyword database from real-world enterprise CA names
2. Add SHA-1 leaf certificate detection via certificate field inspection (not just OpenSSL error string)
3. Cache CERT_NONE connections per IP to reduce overhead of chain subtype detection
4. Validate WEAK_SIGNATURE_ALGORITHM against additional SSL library versions (LibreSSL, BoringSSL)

## Files Referenced
- `tls_policy_adapter/schema.py` — WEAK_SIGNATURE_ALGORITHM literal and risk mapping
- `scripts/run_local_tls_validation.py` — `_classify_ssl_error()` and `_determine_chain_subtype()`
- `scripts/spl_tls_analyze.py` — WEAK_SIGNATURE_ALGORITHM in _RECOMMENDED_ACTIONS
- `scripts/run_real_tls_spl_decision_validation.py` — WEAK_SIGNATURE_ALGORITHM policy mapping
- `tests/test_spl_decision_validation.py` — ALL_CLASSIFICATIONS with WEAK_SIGNATURE_ALGORITHM
- `docs/REAL_DATA_VALIDATION_REPORT.md` — Phase 22 report
- `docs/MEASUREMENT_VALIDITY_AUDIT.md` — Phase 23 report
