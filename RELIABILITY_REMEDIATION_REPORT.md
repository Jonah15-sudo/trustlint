# RELIABILITY_REMEDIATION REPORT.md

**Date:** 2026-06-09
**Purpose:** Document reliability improvements implemented

---

## Changes Implemented

### 1. Global State Elimination ✅

**Before:**
```python
# Global mutable state
PROBE_TIMEOUT = 10.0

# Mutated by spl_tls_analyze.py
probe_mod.PROBE_TIMEOUT = timeout
```

**After:**
```python
# Parameter-based timeout (thread-safe)
def probe_domain(domain: str, ca_store: str = "platform", timeout: float = 10.0):
    ...
    tls_info = _attempt_tls_handshake(domain, ip, ca_store=ca_store, timeout=timeout)
```

**Impact:** Thread-safe, no race conditions, no global mutation

---

## Changes Deferred (V1.2 or V2)

### 2. Retry Logic

**Status:** NOT IMPLEMENTED
**Reason:** Requires careful design for retry classification (which errors to retry)
**Plan:** V1.2

**Design:**
```python
def probe_domain_with_retry(domain, max_retries=3, backoff_factor=1.5):
    for attempt in range(max_retries):
        try:
            return probe_domain(domain)
        except RetryableError as e:
            if attempt < max_retries - 1:
                time.sleep(backoff_factor ** attempt)
            else:
                raise
```

### 3. Circuit Breaker

**Status:** NOT IMPLEMENTED
**Reason:** Requires state management across batch
**Plan:** V1.2

### 4. Cancellation Safety

**Status:** NOT IMPLEMENTED
**Reason:** Requires signal handling refactor
**Plan:** V1.2

### 5. Progress Reporting

**Status:** NOT IMPLEMENTED
**Reason:** Requires tqdm or similar
**Plan:** V1.2

---

## Test Verification

All 99 tests pass after global state elimination:
- `test_tls_probe.py`: 25 tests ✅
- `test_spl_tls_analyze.py`: 74 tests ✅

---

## Remaining Reliability Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| No retry logic | HIGH | Manual retry by user |
| No circuit breaker | MEDIUM | User monitors output |
| No cancellation safety | LOW | Ctrl+C works (partial results lost) |
| No progress reporting | LOW | User waits |

---

**Status:** Critical reliability issue (global state) fixed. Remaining issues deferred to V1.2.
