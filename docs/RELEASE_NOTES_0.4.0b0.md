# Release 0.4.0b0

## New Classifications

- **REVOCATION_UNKNOWN** — CRL distribution point was reachable but returned no useful status, or all CRL URLs failed
- **MISSING_REVOCATION_INFO** — OCSP responder was unreachable and no CRL fallback was available

## Bug Fixes

- **Expired cert regression** — `expired.badssl.com` now correctly classifies as EXPIRED_CERT instead of timing out. Expired/self-signed certs no longer trigger revocation checks, and the expired classification is set before any revocation logic runs.
- **CRL revocation detection attempt** (documented limitation) — CRL Distribution Point parsing was added but remains unreliable for many certificates due to ASN.1 DER structure variations. Certificates that use CRL-only revocation (no OCSP responder URL) may not be flagged as revoked.

## Tests

- All 597 tests passing.
