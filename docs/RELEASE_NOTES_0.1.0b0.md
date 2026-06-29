# Release Notes — spl-tls-analyze v0.1.0b0

**Local Beta Release — Not Production Ready**

## What's Included

`spl-tls-analyze` is a local CLI tool that probes TLS certificate validity for a domain and produces a structured decision (ALLOW / REVIEW / DENY) based on a multi-layer policy engine.

Stack (top to bottom):
- **CLI** (`spl-tls-analyze`) — console output, JSON, Markdown reports
- **Decision Orchestrator** — 8 policy rules across 3 operating profiles
- **TLS Policy Adapter** — maps 12 probe classifications to risk categories
- **TLS Probe** — stdlib `ssl` + `socket` handshake with 11 classification outputs
- **SPL Core** — ML-based evidence pipeline (loaded only via `[spl-core]` extra)
- **OFE** — optional field extraction (observational only, `HOLD_PENDING_REAL_DATA`)

## What Works

- TLS probing for 11 classification outcomes (VALID_TLS, EXPIRED_CERT, WRONG_HOST_CERT, SELF_SIGNED_CERT, etc.)
- Adapter-based risk categorization (7 categories × 5 severities)
- 3 operating profiles (balanced, conservative, strict) with different ALLOW thresholds
- Fallback ALLOW for clean VALID_TLS domains when SPL is unavailable (balanced profile only)
- Structured console output, JSON output, and Markdown reports
- Batch analysis with summary counts per decision
- Exit codes: ALLOW=0, REVIEW=1, DENY=2, error=3, invalid-args=4
- Golden acceptance tests with stable output snapshots
- Zero external dependencies (stdlib only in default mode)
- Editable install via `pip install -e .`

## Default Profile

**Balanced** — the default operating profile:
- ALLOWs clean VALID_TLS directly (via adapter-based fallback when SPL is unavailable)
- REVIEWs on low SPL confidence or non-clean adapter results
- DENYs on CRITICAL adapter severity

## CLI Command Examples

```bash
# Single domain (default balanced profile)
spl-tls-analyze example.com

# Verbose output
spl-tls-analyze example.com --verbose

# Different profile
spl-tls-analyze example.com --profile conservative
spl-tls-analyze example.com --profile strict

# JSON output
spl-tls-analyze example.com --json-out result.json

# Markdown report
spl-tls-analyze example.com --markdown-out report.md

# Batch analysis
spl-tls-analyze example.com github.com stackoverflow.com
```

## Dogfood Results

Tested against 31 real public domains (safe services + badssl.com test cases):

| Metric | Before (Phase 12) | After (Phase 13) |
|--------|--------------------|--------------------|
| ALLOW  | 0                   | 19                 |
| REVIEW | 30                  | 11                 |
| DENY   | 1                   | 1                  |

- 19 clean domains now ALLOW via balanced fallback (adapter-based, not SPL confidence)
- 0 risky domains became ALLOW — fallback guardrails prevent this
- 11 domains remain REVIEW (8 badssl high-risk, 2 probe-limited DNS failures, 1 self-signed)
- 1 DENY (wrong.host.badssl.com — CRITICAL severity)

## Test Count

**530 tests** across 21 test files:

| Test File | Count | Scope |
|-----------|-------|-------|
| test_spl_decision_validation.py | 70 | Modes, leakage, holdout, benchmark |
| test_tls_policy_adapter.py | 69 | Classification, severity, schema |
| test_decision_orchestrator.py | 128 | Rules, fallback, profiles, safety |
| test_spl_tls_analyze.py | 47 | CLI args, output, exit codes |
| test_cli_golden_acceptance.py | 26 | Golden snapshots, batch, contracts |
| test_package_entry.py | 11 | Entry point, packaging |
| test_docker_docs.py | 10 | Dockerfile integrity, smoke tests |
| Other / prior phases | 169 | SPL v7.1 core, historical validation |

## Release Verification Summary

The `verify_release.py` script runs **13 checks** (12 mandatory + 1 optional):

1. Full test suite (530 tests)
2. Compileall (no syntax errors)
3. Golden acceptance tests (26 snapshot tests)
4. CLI mocked smoke test (VALID_TLS → ALLOW via fallback)
5. CLI negative fallback smoke test (5 guardrails)
6. SPL Core integrity (files untouched)
7. OFE status (HOLD_PENDING_REAL_DATA)
8. Package metadata (pyproject.toml)
9. Console entry point (spl-tls-analyze)
10. Entry point tests (11 packaging tests)
11. Install documentation (INSTALL.md + VERSIONING.md)
12. Version consistency (0.1.0b0 across all key files)
13. Docker (optional — file integrity + build if Docker CLI available)

## Known Limitations

See [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) for full details. Key items:

- **Adapter-only mode**: without SPL (`[spl-core]` extra), the tool relies on deterministic adapter-based fallback — not ML-powered confidence scoring
- **Deprecated TLS detection**: best-effort only (depends on OpenSSL negotiation behavior)
- **No CRL/OCSP checking**: revoked certificates not detected via revocation lists
- **Console output format**: unstable — may change between beta versions
- **Live probe behavior**: depends on network conditions, DNS resolution, and remote server behavior
- **OFE is observational only**: not used in decisions, held for real-data validation

## No Production Readiness Disclaimer

This is a **local beta release** (`0.1.0b0`). It is:

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
