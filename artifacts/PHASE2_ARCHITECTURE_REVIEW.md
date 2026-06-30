# TrustLint Phase 2 — Architecture Review

## PR Stack (Bottom-Up)

```
master (cfd90b6)
  └── #3  hardening/repository-root-normalization
        └── #4  hardening/test-collection-and-cli-recovery
              └── #5  hardening/validation-test-contract-cleanup
                    └── #6  hardening/validation-runner-product-recovery  ← current top
```

| PR | Title | Base | Status |
|----|-------|------|--------|
| #3 | refactor(repo): normalize repository root for GitHub automation | master | DRAFT |
| #4 | fix: restore CLI compatibility and resolve CI collection failures | #3 | DRAFT |
| #5 | test: remove obsolete benchmark test contracts | #4 | DRAFT |
| #6 | feat: add offline SPL validation runner | #5 | DRAFT |

## Review Order

Review bottom-up: #3 → #4 → #5 → #6.

## Merge Order

Merge bottom-up only. Each PR must be reviewed, CI-revalidated, and merged before the next.

## Production Path Map

```
CLI (trustlint.cli:main)
  └── analyzer (trustlint.analyzer)
        ├── TLS probe (trustlint.infrastructure.tls_probe)
        │     └── socket + ssl → cipher, version, cert, chain, SAN, compression
        └── OCSP client (trustlint.infrastructure.ocsp.client)
              └── OCSP URL extraction, request construction, response parsing,
                  timeout/error handling, and protected outbound requests
```

## Explicit Boundary

`trustlint.infrastructure.validation_runner` is **offline research/validation only**. It is NOT on the production CLI path. Neither `trustlint.cli` nor `trustlint.analyzer` imports it. Only `tests/test_spl_decision_validation.py` imports it for test coverage.

## Remaining Release Risk

All stacked PRs must be reviewed and CI-revalidated after each eventual merge. Merging any PR may change the base for dependent PRs, requiring rebase and re-test.

## Verdict

**READY FOR INTERNAL DEMO, NOT READY FOR PUBLIC PRODUCTION CLAIMS**
