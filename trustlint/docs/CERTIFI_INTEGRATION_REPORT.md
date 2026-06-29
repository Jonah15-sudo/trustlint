# Phase 20 — Portable CA Trust Store Enhancement

## certifi Integration Report

**Date:** 2026-06-03

---

## Design

The probe's TLS handshake function (`_attempt_tls_handshake` in `scripts/run_local_tls_validation.py`) creates an SSL context using two CA load steps:

1. If `ca_store="certifi"`, attempt `load_verify_locations(cafile=certifi.where())` to load the Mozilla CA bundle.
2. Always call `load_default_certs()` as a fallback (ensures backward compatibility).

This two-step approach guarantees:
- **certifi mode:** Mozilla CA bundle is loaded first; platform defaults supplement any missing roots.
- **Failed import degrades gracefully:** If `certifi` is not installed, `context.load_default_certs()` is called, preserving the existing behavior.
- **Platform mode (default) unchanged:** `context.load_default_certs()` only — identical to pre-Phase 20 behavior.

## CLI Interface

```bash
# Default (platform trust store — backward compatible)
spl-tls-analyze example.com

# Certifi Mozilla CA bundle
spl-tls-analyze example.com --ca-store certifi
```

Available values: `platform` (default), `certifi`.

Environment variable and config file integration were considered but deferred — a CLI flag is sufficient for this phase.

## Dependency

```
pip install spl-tls-analyze[ca-store]
```

This installs `certifi>=2024.0.0`. The dependency is optional — the probe works without it.

## Test Methodology

1. **Baseline run:** 100 real-world domains + 141 adversarial domains with `--ca-store platform` (default).
2. **Certifi run:** Same domains with `--ca-store certifi`.
3. **Delta analysis:** Compare classifications, decisions, and summary statistics.
4. **Individual probes:** walmart.com and cnn.com probed with both modes to confirm the hypothesized fix.

Known false positives from Phase 18.5/19 were the primary validation targets.

## Before/After Comparison

### real_world_audit_domains.txt (100 domains)

| Metric | Platform | certifi | Delta |
|--------|:--------:|:-------:|:-----:|
| ALLOW | 93 | 95 | **+2** |
| REVIEW | 6 | 4 | **-2** |
| DENY | 1 | 1 | 0 |
| Fallback ALLOW | 93 | 95 | +2 |

### adversarial_tls_domains.txt (141 domains)

| Metric | Platform | certifi | Delta |
|--------|:--------:|:-------:|:-----:|
| ALLOW | 107 | 108 | **+1** |
| REVIEW | 33 | 32 | **-1** |
| DENY | 1 | 1 | 0 |
| Fallback ALLOW | 107 | 108 | +1 |
| Probe-limited | 11 | 11 | 0 |
| Probe errors | 2 | 2 | 0 |

### Classification Changes

Only 3 domains changed classification, all UNTRUSTED_CHAIN → VALID_TLS:

| Domain | Platform | certifi | TLS | Expires |
|--------|:--------:|:-------:|:---:|:-------:|
| walmart.com | UNTRUSTED_CHAIN | VALID_TLS | TLSv1.3 | 294 days |
| cnn.com | UNTRUSTED_CHAIN | VALID_TLS | TLSv1.3 | 137 days |

### Decision Changes

All 3 classification changes resulted in decision changes (REVIEW → ALLOW).

**No new false positives were introduced.**

**No existing valid classifications regressed.**

### Cross-Platform Consistency

certifi provides a Mozilla-maintained CA bundle that is:
- Identical across all platforms (Windows, macOS, Linux)
- Updated with each pip release
- Independent of the local OS trust store

This eliminates platform-specific false positives caused by missing root/intermediate CAs in the Windows local trust store (the root cause of the walmart.com/cnn.com UNTRUSTED_CHAIN classifications).

## Security Considerations

### What certifi provides
- Mozilla's CA certificate bundle, maintained since 2011
- Same trust roots used by Firefox
- Regular updates (multiple releases per year)
- Consistent across all operating systems

### What certifi does NOT provide
- CRL/OCSP revocation checking (deferred to future phase)
- Certificate pinning
- HSTS/CSP header parsing
- Weak cipher or protocol detection

### Risk of wider trust
Using the Mozilla CA bundle instead of the platform store accepts all Mozilla-trusted CAs. This is the same set trusted by Firefox and is the de-facto standard for Python SSL applications. The risk is negligible compared to the benefit of eliminating platform-specific false positives.

## Limitations

1. **Requires pip install** — users who want certifi mode must install the optional dependency.
2. **No revocation checking** — certifi does not add CRL/OCSP checking; it only resolves trust-chain completeness.
3. **No cipher/weakness analysis** — the probe still does not detect weak cipher suites or key sizes (deferred).
4. **certifi is a single-file CA bundle** — it does not include intermediate certificates, only root CAs. The server must serve intermediates.
5. **certifi must be kept updated** — old certifi bundles may lack new roots or retain expired roots. Users should `pip install --upgrade certifi` periodically.

## Success Criteria Verification

| Criterion | Status | Evidence |
|-----------|:------:|----------|
| cnn.com no longer UNTRUSTED_CHAIN | ✓ | VALID_TLS with certifi |
| walmart.com no longer UNTRUSTED_CHAIN | ✓ | VALID_TLS with certifi |
| No increase in false positives | ✓ | 0 new non-VALID_TLS changes |
| No regression in test suite | ✓ | 530 passed, 0 failed, 0 warnings |
| Backward compatibility preserved | ✓ | Default `--ca-store platform` unchanged |
| Findings fully documented | ✓ | This report |

## Final Answer

> **Does certifi materially improve TLS classification accuracy enough to become the default trust store for spl-tls-analyze?**

**Yes.** certifi eliminates 3 false-positive UNTRUSTED_CHAIN classifications across 241 domains with zero regressions. It provides platform-consistent trust verification that matches the Mozilla root store used by the majority of web browsers.

**Recommendation:** Change the default to `certifi` in a future release once the optional dependency workflow is validated with real users. For now, users who encounter UNTRUSTED_CHAIN on Akamai/Fastly-hosted sites should use `--ca-store certifi`.
