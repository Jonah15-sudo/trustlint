# Release Notes — spl-tls-analyze v0.2.0b0

**Local Beta Release — Not Production Ready**

## What's New Since v0.1.0b0

### SPL Integration (`--spl` flag)

Added `--spl` CLI flag that creates an in-memory `EvidencePipeline` from `configs/features.dsl` and passes real `spl_decision`/`spl_confidence` to the Decision Orchestrator. SPL Core remains unmodified.

Usage:
```bash
pip install -e ".[spl-core]"
spl-tls-analyze example.com --spl
```

### OCSP Revocation Checking

Added `scripts/ocsp_checker.py` — a stdlib-only OCSP checker with manual ASN.1 DER parsing. During TLS probing, the checker:
- Extracts AIA OCSP responder URLs from the server certificate
- Performs an HTTP POST OCSP request with a 2-second timeout
- Classifies the result: `good`, `revoked`, `unknown`, or `unreachable`

New classifications:
- **REVOKED_CERT** (SECURITY_RISK/CRITICAL/DENY) — certificate is revoked
- **OCSP_UNREACHABLE** (AVAILABILITY_RISK/MEDIUM/REVIEW) — OCSP responder unreachable

Dogfood result: `revoked.badssl.com` is now correctly detected.

### Deprecated TLS Version Detection

After a `VALID_TLS` primary probe, a secondary probe forces `minimum_version=maximum_version=ssl.TLSVersion.TLSv1_1`. If the server accepts the connection, classification becomes `DEPRECATED_TLS_VERSION`.

If TLSv1.1 is unavailable on the platform, the check reports `deprecated_tls_check="unavailable_on_platform"`.

### Other Changes

- **Test suite**: 557 tests (up from 530 in v0.1.0b0) — 17 new OCSP tests, 5 new deprecated TLS tests, 5 updated schema tests
- **Golden fixtures**: Regenerated for all 13 classification scenarios
- **KNOWN_LIMITATIONS.md**: OCSP section rewritten from "No CRL/OCSP Checking" to "OCSP Checking is Best-Effort"; deprecated TLS section rewritten
- **README.md**: "What It Does Today" expanded with OCSP, deprecated TLS, SPL integration, and 5 new risk categories; "What It Does Not Do" updated to remove OCSP entry

## What Works

- TLS probing for 15 classification outcomes (VALID_TLS, EXPIRED_CERT, WRONG_HOST_CERT, SELF_SIGNED_CERT, REVOKED_CERT, OCSP_UNREACHABLE, DEPRECATED_TLS_VERSION, etc.)
- OCSP revocation checking via AIA responder URLs
- Deprecated TLS version detection (secondary TLSv1.1 probe)
- SPL evidence pipeline integration (`--spl` flag, `[spl-core]` extra required)
- Adapter-based risk categorization (7 categories × 5 severities)
- 3 operating profiles (balanced, conservative, strict) with different ALLOW thresholds
- Fallback ALLOW for clean VALID_TLS domains when SPL is unavailable (balanced profile only)
- Structured console output, JSON output, and Markdown reports
- Batch analysis with summary counts per decision
- Exit codes: ALLOW=0, REVIEW=1, DENY=2, error=3, invalid-args=4
- Golden acceptance tests with stable output snapshots
- Zero external dependencies (stdlib only in default mode)
- Editable install via `pip install -e .`

## Test Count

**557 tests** across 23 test files:

| Test File | Count | Scope |
|-----------|-------|-------|
| test_spl_decision_validation.py | 70 | Modes, leakage, holdout, benchmark |
| test_tls_policy_adapter.py | 74 | Classification, severity, schema, OCSP fields |
| test_decision_orchestrator.py | 128 | Rules, fallback, profiles, safety |
| test_spl_tls_analyze.py | 52 | CLI args, output, exit codes, OCSP/deprecated TLS |
| test_cli_golden_acceptance.py | 26 | Golden snapshots, batch, contracts |
| test_package_entry.py | 11 | Entry point, packaging |
| test_docker_docs.py | 10 | Dockerfile integrity, smoke tests |
| Other / prior phases | 186 | SPL v7.1 core, historical validation |

## Release Verification Summary

The `verify_release.py` script runs **14 checks** (12 mandatory + 2 optional):

1. Full test suite (557 tests)
2. Compileall (no syntax errors)
3. Golden acceptance tests (26 snapshot tests)
4. CLI mocked smoke test (VALID_TLS → ALLOW via balanced fallback)
5. CLI negative fallback smoke test (5 guardrails)
6. SPL Core integrity (files untouched)
7. OFE status (HOLD_PENDING_REAL_DATA)
8. Package metadata (pyproject.toml)
9. Console entry point (spl-tls-analyze)
10. Entry point tests (11 packaging tests)
11. Install documentation (INSTALL.md + VERSIONING.md)
12. Version consistency (0.2.0b0 across all key files)
13. Docker (optional — file integrity + build if Docker CLI available)
14. VPS dry-run docs (optional — file integrity only)

## Known Limitations

See [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) for full details. Key items:

- **OCSP checking is best-effort**: depends on AIA responder availability and network conditions; does not use OCSP stapling; cannot detect revocation when the responder is unreachable
- **Deprecated TLS detection is best-effort**: depends on OpenSSL TLSv1.1 support; unavailable on some platforms (e.g., newer OpenSSL 3.x builds that remove TLSv1.1)
- **Adapter-only mode**: without SPL (`[spl-core]` extra), the tool relies on deterministic adapter-based fallback — not ML-powered confidence scoring
- **Console output format**: unstable — may change between beta versions
- **Live probe behavior**: depends on network conditions, DNS resolution, and remote server behavior
- **OFE is observational only**: not used in decisions, held for real-data validation

## No Production Readiness Disclaimer

This is a **local beta release** (`0.2.0b0`). It is:

- NOT production-ready
- NOT published on PyPI
- NOT intended for security-critical decision-making
- NOT a substitute for proper certificate validation in production systems

The ALLOW decision for any domain indicates only that the tool's local policy considers it acceptable — it does not guarantee the domain is trustworthy or safe.

## OFE Status

**HOLD_PENDING_REAL_DATA** — the optional field extraction (OFE) component is present in the codebase but:
- Observational only (not used in any decision)
- Requires real production TLS traffic data to validate
- Held pending availability of such data
