# PROJECT_MAP.md — TrustLint V1.1

**Last Updated:** 2026-06-09
**Version:** 1.0.0-consolidated (remediation applied)

---

## TECH_STACK

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.10+ |
| TLS Probing | ssl (stdlib) | — |
| OCSP | asn1 (stdlib) | — |
| CLI | argparse (stdlib) | — |
| Testing | pytest | 8.0+ |
| Coverage | pytest-cov | — |
| Containerization | Docker | — |
| CI/CD | GitHub Actions | — |
| Package Manager | pip | — |
| Build System | pyproject.toml | — |

**Zero Runtime Dependencies** — Pure Python stdlib.

---

## SYSTEM_FLOW

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI INPUT                            │
│  trustlint example.com --profile strict --format json       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    INPUT VALIDATION                         │
│  • Domain format validation                                 │
│  • Profile validation (conservative/balanced/strict)        │
│  • Configuration validation                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    TLS PROBING LAYER                        │
│  • DNS resolution                                           │
│  • TCP connection                                           │
│  • TLS handshake (timeout parameter, not global)            │
│  • Certificate chain validation                             │
│  • OCSP/CRL revocation checking (2s timeout)                │
│  • Deprecated TLS detection                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 POLICY ADAPTER LAYER                        │
│  • Map classification → risk_category                       │
│  • Map risk_category → severity                             │
│  • Map severity → action_hint                               │
│  • Generate policy_reason                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 DECISION ORCHESTRATOR                        │
│  • Apply security profile (conservative/balanced/strict)    │
│  • Combine adapter + SPL outputs                            │
│  • Generate final decision (ALLOW/REVIEW/DENY)              │
│  • Generate risk level (NONE/LOW/MEDIUM/HIGH/CRITICAL)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   OUTPUT FORMATTING                         │
│  • Console (human-readable)                                 │
│  • JSON (versioned schema)                                  │
│  • Markdown (report format)                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## ARCHITECTURE

### Production Modules

```
trustlint/
├── decision_orchestrator/    # Decision logic
│   ├── policy.py            # Orchestration rules
│   ├── reporter.py          # Output formatting
│   └── schema.py            # Type definitions
├── tls_policy_adapter/       # Risk classification
│   ├── risk_policy.py       # Classification logic
│   ├── schema.py            # Risk map
│   └── evidence_adapter.py  # Evidence enrichment
├── scripts/
│   ├── spl_tls_analyze.py   # Main CLI entry point
│   ├── run_local_tls_validation.py  # TLS probe (timeout as parameter)
│   └── ocsp_checker.py      # OCSP verification (2s timeout)
├── configs/                  # Configuration files
├── datasets/                 # Domain data
└── tests/                    # Test suite
```

### Research Modules (Gated Behind --spl-unsafe)

```
├── spl_v7/                   # SPL Core (research)
├── frontier/                 # Exploration sidecar
├── weakness_mapper/          # Weakness discovery
├── experiments/              # Experiment runner
└── orthogonal_engine/        # Orthogonal analysis
```

---

## DECISIONS

| Decision | Date | Rationale |
|----------|------|-----------|
| Use V3 as primary reference | 2026-06-09 | 597 tests, comprehensive features |
| Gate research behind --spl-unsafe | 2026-06-09 | Production safety |
| Eliminate global mutable state | 2026-06-09 | Thread safety |
| Defer packaging redesign to V1.2 | 2026-06-09 | Risk mitigation |
| Defer retry logic to V1.2 | 2026-06-09 | Requires careful design |

---

## REGRESSION_GUARDS

### Test Coverage

| Module | Tests | Status |
|--------|-------|--------|
| test_tls_probe.py | 25 | ✅ PASSING |
| test_spl_tls_analyze.py | 74 | ✅ PASSING |
| test_decision_orchestrator.py | ~80 | ✅ PASSING |
| test_tls_policy_adapter.py | ~45 | ✅ PASSING |
| **Total** | **~224** | **✅ ALL PASSING** |

### CI/CD Pipeline

```yaml
- Run test suite
- Check type hints (planned V1.2)
- Lint code (planned V1.2)
- Build package
- Verify release
```

---

## REMOVED_ITEMS

| Item | Reason | Date |
|------|--------|------|
| Global PROBE_TIMEOUT mutation | Thread-unsafe | 2026-06-09 |
| Global RATE_LIMIT_SECONDS mutation | Thread-unsafe | 2026-06-09 |

---

## KNOWN_LIMITATIONS

1. **No retry logic:** Transient network failures cause permanent failures
2. **No concurrent probing:** Sequential by default (100x slower than necessary)
3. **No DNS caching:** Redundant DNS lookups in batch mode
4. **No progress reporting:** Poor UX on large batches
5. **Packaging issues:** sys.path hacks in 20+ files
6. **Version mismatch:** pyproject.toml says 0.3.2b0, README says 1.0.0

---

## ORPHANS_AND_PENDING

### Pending Decisions

| Decision | Context | Required Input |
|----------|---------|----------------|
| Version numbering | pyproject.toml vs README | Product decision |
| Package restructuring | sys.path hacks | Architecture decision |
| Concurrent probing | Thread pool design | Performance decision |

### Orphaned Items

| Item | Location | Status |
|------|----------|--------|
| orthogonal_engine/ | Root directory | Research only, not used in production |
| experiments/ | Root directory | Research only, not used in production |

---

## VERSION_HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0-consolidated | 2026-06-09 | Multi-version consolidation |
| 1.0.0-remediated | 2026-06-09 | Global state elimination, hostile review validation |

---

**Maintained By:** Project Memory Authority
