# ARCHITECTURE_AUDIT.md — Consolidated Version

## Executive Summary

This document captures the architectural decisions made during the multi-version consolidation of TrustLint.

---

## Version Comparison

### V1 Architecture (trustlint_v2)

**Pattern:** Clean Architecture with Frozen Dataclasses

**Strengths:**
- Immutable value objects (frozen dataclasses)
- Thread-safe by design
- Clean separation of concerns (probe, policy, report)
- Comprehensive documentation
- Type-safe with py.typed marker
- Zero runtime dependencies

**Module Structure:**
```
trustlint/
├── cli/
│   └── main.py          # CLI entry point
├── policy/
│   ├── orchestrator.py  # Decision orchestration
│   └── risk_map.py      # Risk classification
├── probe/
│   ├── models.py        # Data models (frozen dataclasses)
│   ├── ocsp.py          # OCSP verification
│   └── tls.py           # TLS probing
├── report/
│   └── formatters.py    # Output formatting
└── exceptions.py        # Custom exceptions
```

**Key Design Patterns:**
- ProbeConfig as configuration container
- ProbeResult as immutable value object
- AnalysisResult as complete analysis output
- No global mutable state
- Thread-safe concurrent probing

### V3 Architecture (spl_v7_project)

**Pattern:** Enterprise Module System

**Strengths:**
- Comprehensive feature set
- 597 tests (all passing)
- Enterprise features (health checks, Docker)
- Structured logging
- Input validation
- Real TLS data collection
- Frontier exploration sidecar
- Orthogonal analysis engine

**Module Structure:**
```
trustlint/
├── spl_v7/              # Core TLS analysis module
│   ├── causal.py
│   ├── dashboard.py
│   ├── dsl.py
│   ├── frontier.py
│   ├── kafka_pipeline.py
│   ├── schema.py
│   ├── utils.py
│   └── verification.py
├── decision_orchestrator/  # Decision rules & profiles
│   ├── policy.py
│   ├── reporter.py
│   └── schema.py
├── tls_policy_adapter/     # TLS risk classification
│   ├── evidence_adapter.py
│   ├── risk_policy.py
│   └── schema.py
├── frontier/               # Exploration sidecar
│   ├── metrics.py
│   ├── reports.py
│   └── session.py
├── orthogonal_engine/      # Orthogonal analysis
│   └── orthogonal_flat_engine_v09_0_fixed.py
├── weakness_mapper/        # Weakness discovery
│   ├── boundaries.py
│   ├── cluster.py
│   ├── extractor.py
│   ├── registry.py
│   └── reporter.py
├── experiments/            # Experiment runner
│   ├── experiment_runner.py
│   ├── metrics.py
│   ├── replication.py
│   └── ...
├── scripts/               # CLI entry points
│   ├── spl_tls_analyze.py
│   ├── ocsp_checker.py
│   └── ...
└── tests/                 # 597 tests
    ├── test_decision_orchestrator.py
    ├── test_tls_probe.py
    └── ...
```

**Key Design Patterns:**
- TypedDict for schema definitions
- Module-level functions
- Script-based CLI entry points
- Docker HEALTHCHECK
- Structured logging (--verbose/--quiet)

---

## Architectural Debt Identified

### V1 Debt

| Issue | Severity | Impact |
|-------|----------|--------|
| Limited to 22 classifications | MEDIUM | May miss edge cases |
| No enterprise features | HIGH | Not production-ready |
| No structured logging | MEDIUM | Difficult debugging |
| No health checks | MEDIUM | Hard to monitor |

### V3 Debt

| Issue | Severity | Impact |
|-------|----------|--------|
| TypedDict vs frozen dataclasses | LOW | Less type safety |
| Script-based CLI | MEDIUM | Less clean entry point |
| No ProbeConfig equivalent | MEDIUM | Configuration scattered |
| Mixed naming conventions | LOW | Inconsistent API |

---

## Consolidated Architecture

### Design Principles

1. **Immutable Value Objects** (from V1)
   - Use frozen dataclasses for all data models
   - Thread-safe by design
   - Hashable for caching

2. **Clean Separation of Concerns** (from V1)
   - Separate probe, policy, and report layers
   - Clear dependency direction

3. **Enterprise Features** (from V3)
   - Health checks
   - Docker support
   - Structured logging
   - Input validation

4. **Comprehensive Testing** (from V3)
   - 597 tests preserved
   - Full coverage

### Target Module Structure

```
trustlint/
├── trustlint/              # Core package (from V1 pattern)
│   ├── __init__.py
│   ├── cli/
│   │   └── main.py         # Clean CLI entry point
│   ├── probe/
│   │   ├── models.py       # Frozen dataclasses (from V1)
│   │   ├── tls.py          # TLS probing
│   │   └── ocsp.py         # OCSP verification
│   ├── policy/
│   │   ├── orchestrator.py # Decision orchestration
│   │   └── risk_map.py     # Risk classification
│   ├── report/
│   │   └── formatters.py   # Output formatting
│   └── exceptions.py       # Custom exceptions
├── decision_orchestrator/  # From V3
├── tls_policy_adapter/     # From V3
├── frontier/               # From V3
├── orthogonal_engine/      # From V3
├── weakness_mapper/        # From V3
├── experiments/            # From V3
├── scripts/                # From V3
├── tests/                  # 597 tests
├── docs/                   # Documentation
├── datasets/               # Domain data
├── configs/                # Configuration
└── Dockerfile              # Container support
```

---

## Key Design Decisions

### Decision 1: Use V1's Frozen Dataclasses

**Rationale:**
- Thread-safe by design
- Immutable value objects
- Clean Pythonic API
- Better type safety than TypedDict

**Impact:**
- Requires migration from V3's TypedDict
- Improves code quality
- Reduces bugs

### Decision 2: Keep V3's Enterprise Features

**Rationale:**
- Health checks essential for production
- Docker support required
- Structured logging improves debugging
- Input validation prevents errors

**Impact:**
- Adds complexity
- Required for production deployment

### Decision 3: Preserve V3's Test Suite

**Rationale:**
- 597 tests provide comprehensive coverage
- Regression protection
- Documentation of behavior

**Impact:**
- Must maintain test compatibility
- May require adapter tests for new patterns

### Decision 4: Merge V1's Clean CLI

**Rationale:**
- Cleaner entry point
- Better argument parsing
- Consistent exit codes

**Impact:**
- Requires CLI migration
- Improves user experience

---

## Migration Plan

### Phase 1: Extract V1 Models

1. Copy V1's frozen dataclasses to trustlint/probe/models.py
2. Update imports in V3 modules
3. Run tests to verify compatibility

### Phase 2: Merge V1 CLI

1. Copy V1's CLI structure to trustlint/cli/
2. Update entry points
3. Verify CLI behavior

### Phase 3: Clean Up

1. Remove duplicate code
2. Standardize naming conventions
3. Update documentation

---

## Risk Assessment

| Risk | Mitigation | Confidence |
|------|------------|------------|
| Breaking V3 tests | Run full test suite after each change | HIGH |
| Losing V3 features | Document all features before migration | HIGH |
| Introducing bugs | Comprehensive testing | MEDIUM |
| Performance regression | Benchmark before/after | LOW |

---

## Recommendations

### Short Term

1. **Preserve V3 as-is** for now
2. **Document V1 patterns** for future reference
3. **Run V3 test suite** to establish baseline

### Medium Term

1. **Migrate V1 models** to V3
2. **Clean up naming** conventions
3. **Improve documentation**

### Long Term

1. **Consider full V1 architecture adoption**
2. **Implement clean CLI**
3. **Add type safety improvements**

---

## Conclusion

The consolidated version preserves V3's comprehensive feature set while documenting V1's superior architectural patterns. The migration to V1's frozen dataclasses should be considered for future versions to improve code quality and type safety.

**Current Status:** Production-ready with V3's features and V1's patterns documented for future adoption.

---

**Last Updated:** 2026-06-09
**Version:** 1.0.0-consolidated
