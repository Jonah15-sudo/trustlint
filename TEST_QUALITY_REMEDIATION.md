# TEST_QUALITY_REMEDIATION.md

**Date:** 2026-06-09
**Purpose:** Document test quality improvements

---

## Issues Identified

### 1. Source Code Inspection Tests

**Status:** NOT FIXED
**Reason:** Tests still inspect `__code__` and `getsource()`
**Files:** `tests/test_tls_probe.py` lines 79, 82, 89
**Plan:** V1.2

### 2. Configuration-Only Tests

**Status:** NOT FIXED
**Reason:** Many tests check dictionary keys, not behavior
**Files:** `tests/test_tls_probe.py`, `tests/test_decision_orchestrator.py`
**Plan:** V1.2

### 3. No Integration Tests

**Status:** NOT FIXED
**Reason:** Requires real TLS connections
**Plan:** V1.2

---

## What Was Verified

All 99 tests pass after global state elimination. No regressions.

---

## Recommended Test Quality Improvements (V1.2)

### 1. Replace Source Inspection with Behavioral Tests

```python
# BEFORE (brittle):
src = inspect.getsource(_attempt_tls_handshake)
self.assertIn('"cipher_name": None', src)

# AFTER (behavioral):
result = _attempt_tls_handshake("example.com", "1.2.3.4")
self.assertIn("cipher_name", result)
self.assertIsNone(result["cipher_name"])
```

### 2. Add Integration Tests

```python
@pytest.mark.integration
def test_real_tls_probe():
    result = probe_domain("google.com")
    assert result["classification"] == "VALID_TLS"
```

### 3. Add Coverage Measurement

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = "--cov=trustlint --cov-report=term-missing"
```

---

## Current Test Quality

| Metric | Value |
|--------|-------|
| Test count | 99 (core modules) |
| Pass rate | 100% |
| Coverage | Unknown |
| Integration tests | 0 |
| Behavioral tests | ~50% |

---

**Status:** Test quality issues documented. Improvements deferred to V1.2.
