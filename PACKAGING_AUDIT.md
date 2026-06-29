# PACKAGING_AUDIT.md

**Date:** 2026-06-09
**Purpose:** Document packaging issues and remediation plan

---

## Issues Identified

### 1. sys.path Hacks (20+ files)

**Status:** NOT FIXED
**Reason:** Requires package restructuring
**Plan:** V1.2

**Files affected:**
- `scripts/spl_tls_analyze.py`
- `scripts/verify_release.py`
- `tests/test_*.py` (10+ files)

### 2. Version Mismatch

**Status:** NOT FIXED
**Reason:** Requires decision on versioning strategy
**Plan:** V1.1

**Current state:**
- `pyproject.toml`: "0.3.2b0"
- README: "1.0.0-consolidated"

### 3. scripts/ as Package

**Status:** NOT FIXED
**Reason:** Requires entry point refactor
**Plan:** V1.2

---

## Recommended Fix (V1.2)

### Package Structure

```
trustlint/
├── trustlint/              # Main package
│   ├── __init__.py
│   ├── cli.py              # CLI entry point
│   ├── probe.py            # TLS probe
│   ├── policy.py           # Decision orchestrator
│   ├── adapter.py          # Risk adapter
│   └── ocsp.py             # OCSP checker
├── pyproject.toml
└── tests/
```

### pyproject.toml

```toml
[project.scripts]
trustlint = "trustlint.cli:main"
```

---

## Current Workaround

The sys.path hacks work because:
1. Tests are run from project root
2. CLI is run from project root
3. Docker sets WORKDIR /app

**Risk:** Low for current usage
**Impact:** May break if installed via pip in different environment

---

**Status:** Packaging issues documented. Fixes deferred to V1.2.
