# Adversarial Validation Plan

**Phase 19**
**Date:** 2026-06-03
**Version:** 1.0

---

## Purpose

Stress-test `spl-tls-analyze` v0.1.0b0 against adversarial and edge-case TLS targets to discover failure modes before any future development.

This is an **evidence-gathering phase only**. No SPL Core changes, no policy changes, no feature additions, no fallback changes.

## Scope

The validation covers:

| Category | Domains | Purpose |
|----------|--------:|---------|
| badssl.com edge cases | 29 | Stress-test all known TLS failure modes |
| Cloudflare CDN | 12 | Investigate CDN-related trust issues |
| Fastly CDN | 11 | Replicate cnn.com UNTRUSTED_CHAIN finding |
| Akamai CDN | 11 | Replicate walmart.com UNTRUSTED_CHAIN finding |
| CloudFront/AWS CDN | 12 | Investigate AWS-hosted trust patterns |
| Government (intl) | 17 | Test geographically diverse gov sites |
| Universities (intl) | 19 | Test diverse edu deployments |
| Small independent | 17 | Test less-maintained TLS configs |
| Slow/unusual TLS | 14 | Test nonstandard TLS deployments |
| **Total** | **~142** | |

## Validation Questions

1. Which domains produced REVIEW?
2. Which domains produced DENY?
3. Which findings appear to be false positives?
4. Which findings appear to be false negatives?
5. Are any major production sites incorrectly classified?
6. Are there recurring CDN-related trust issues?
7. Does runtime remain stable?
8. Are there probe crashes?
9. Are there timeout clusters?
10. Which known limitations were observed in practice?
11. Which limitations appear most operationally important?
12. Is the balanced profile still practical after adversarial testing?

## Methodology

### Probe Configuration

| Parameter | Value |
|-----------|-------|
| Profile | balanced (default) |
| Timeout | 10 seconds per domain |
| Rate limit | 1.0s between probes |
| Output | JSON (full per-domain) |
| Mode | Adapter-only (no SPL) |

### Analysis Approach

1. **Per-domain decision tracing**: Each domain's decision path is traced through the orchestrator rules (same methodology as Phase 18.5).

2. **CDN pattern analysis**: Results are grouped by CDN provider to identify recurring trust issues.

3. **Badssl edge case coverage**: All available badssl.com subdomains are tested to verify the tool handles every documented failure mode.

4. **False positive identification**: A finding is flagged as a false positive candidate if a well-known production site (e.g., major CDN, top-1k Alexa) produces a non-ALLOW decision.

5. **False negative identification**: A finding is flagged as a false negative candidate if a known-broken domain (e.g., expired.badssl.com) produces ALLOW.

6. **Stability measurement**: Runtime, timeouts, and crash counts are tracked across the full batch.

## Deliverables

| File | Description |
|------|-------------|
| `datasets/adversarial_tls_domains.txt` | Domain list |
| `docs/ADVERSARIAL_VALIDATION_PLAN.md` | This document |
| `scripts/run_adversarial_validation.py` | Validation runner |
| `reports/adversarial_validation/ADVERSARIAL_VALIDATION_REPORT.md` | Full report |
| `reports/adversarial_validation/adversarial_summary.json` | Structured metrics |

## Constraints

- No SPL Core modifications
- No SPL integration
- No OFE promotion
- No architecture changes
- No policy changes
- No fallback changes
- No feature additions
- All existing tests must continue to pass
