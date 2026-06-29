# STATE_MANAGEMENT_REPORT.md

**Date:** 2026-06-09
**Purpose:** Eliminate global mutable state from production code

---

## Problem Analysis

### Current Global State

```python
# scripts/run_local_tls_validation.py
PROBE_TIMEOUT = 10.0      # MUTATED by spl_tls_analyze.py
RATE_LIMIT_SECONDS = 1.0   # MUTATED by main()
DEFAULT_PORT = 443         # Constant (safe)
REPORT_DIR = "reports/..." # Constant (safe)
```

### How State Is Mutated

```python
# scripts/spl_tls_analyze.py (lines 205-211)
import scripts.run_local_tls_validation as probe_mod
original_timeout = probe_mod.PROBE_TIMEOUT
probe_mod.PROBE_TIMEOUT = timeout  # MUTATION
try:
    raw = probe_domain(domain, ca_store=ca_store)
finally:
    probe_mod.PROBE_TIMEOUT = original_timeout  # RESTORE
```

### Why This Is Dangerous

1. **Not thread-safe:** Two threads with different timeouts corrupt each other
2. **Race condition:** `finally` restores original, not the value it set
3. **Hidden dependency:** Functions depend on global state, not parameters
4. **Hard to test:** Cannot test with different timeouts without mutation

---

## Affected Functions

| Function | Uses PROBE_TIMEOUT | Uses RATE_LIMIT |
|----------|-------------------|-----------------|
| `_attempt_tls_handshake()` | Yes (5 places) | No |
| `_check_deprecated_tls()` | Yes (1 place) | No |
| `_determine_chain_subtype()` | Yes (1 place) | No |
| `probe_domain()` | Yes (1 place) | No |
| `main()` | Yes (prints) | Yes (sleep) |

---

## Remediation Strategy

### Step 1: Add timeout parameter to internal functions

```python
def _attempt_tls_handshake(
    domain: str,
    ip: str,
    ca_store: str = "platform",
    timeout: float = 10.0,  # NEW PARAMETER
) -> Dict[str, Any]:
    ...
    with socket.create_connection((ip, DEFAULT_PORT), timeout=timeout) as sock:
```

### Step 2: Add timeout parameter to probe_domain

```python
def probe_domain(
    domain: str,
    ca_store: str = "platform",
    timeout: float = 10.0,  # NEW PARAMETER
) -> Dict[str, Any]:
    ...
```

### Step 3: Update spl_tls_analyze.py to pass timeout

```python
# BEFORE (unsafe):
probe_mod.PROBE_TIMEOUT = timeout
raw = probe_domain(domain, ca_store=ca_store)

# AFTER (safe):
raw = probe_domain(domain, ca_store=ca_store, timeout=timeout)
```

### Step 4: Keep constants as module-level (safe)

```python
DEFAULT_PORT = 443  # Constant, safe to keep
REPORT_DIR = "reports/..."  # Constant, safe to keep
```

---

## Implementation Plan

### Files to Modify

1. `scripts/run_local_tls_validation.py` — Add timeout parameter to functions
2. `scripts/spl_tls_analyze.py` — Pass timeout to probe_domain()
3. `tests/test_tls_probe.py` — Update tests for new parameter

### Backward Compatibility

- `probe_domain(domain)` still works (timeout defaults to 10.0)
- `probe_domain(domain, timeout=5.0)` works (new parameter)
- No breaking changes

---

## Impact Assessment

| Change | Risk | Impact |
|--------|------|--------|
| Add timeout parameter | LOW | Thread safety |
| Update spl_tls_analyze.py | LOW | Remove mutation |
| Update tests | LOW | Test new parameter |

**No functional changes.** Only parameter passing changes.

---

## Verification

After implementation:
1. All tests pass
2. CLI works with `--timeout` flag
3. No global state mutation
4. Thread-safe (can be verified with concurrency test)

---

**Status:** Ready for implementation
