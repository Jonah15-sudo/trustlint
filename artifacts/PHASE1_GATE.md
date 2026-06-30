# TrustLint Phase 1 Gate Report

## Execution Summary

**Date:** 2026-06-30
**Branch:** hardening/validation-runner-product-recovery (top of stack)
**Last CI commit:** e668f40 (new commit pending after TLS probe fixes)

## PR Stack

| PR | Title | Head Branch | Base Branch | Status |
|----|-------|-------------|-------------|--------|
| #3 | refactor(repo): normalize repository root for GitHub automation | hardening/repository-root-normalization | master | DRAFT |
| #4 | fix: restore CLI compatibility and resolve CI collection failures | hardening/test-collection-and-cli-recovery | hardening/repository-root-normalization | DRAFT |
| #5 | test: remove obsolete benchmark test contracts | hardening/validation-test-contract-cleanup | hardening/test-collection-and-cli-recovery | DRAFT |
| #6 | feat: add offline SPL validation runner | hardening/validation-runner-product-recovery | hardening/validation-test-contract-cleanup | DRAFT |

## Gate Results (Local Pre-Push Audit)

### 1. uv lock --check
**Status:** PASS
**Output:** Resolved 38 packages in 1ms

### 2. uv sync --frozen --extra dev --extra spl-core
**Status:** PASS
**Output:** Checked 29 packages in 3ms

### 3. uv run python -m compileall trustlint scripts -q
**Status:** PASS
**Output:** No errors

### 4. uv pip check
**Status:** PASS
**Output:** All installed packages are compatible

### 5. uv run pytest -m "not network and not slow" -q --tb=short -rs
**Status:** PASS
**Results:**
- Passed: 823
- Skipped: 2
- Deselected: 2
- Subtests passed: 54
- Collection errors: 0

#### Skipped Tests (Exact Names and Reasons)

| # | Test File | Test Name | Skip Reason | Covers OCSP/CertChain/TLS/SilentFails/Baseline/ProdCorrectness? |
|---|-----------|-----------|-------------|-------------------------------------------------------------------|
| 1 | `tests/test_spl_decision_validation.py:703` | `test_benchmark_report_gate` | "Benchmark report not yet generated" | NO — benchmark report generation is a CI artifact, not a security/correctness behavior |
| 2 | `tests/test_tls_probe.py:117` | `test_static_rsa_override` | "Network test - requires live connection to dh2048.badssl.com" | NO — network-dependent test, correctly excluded by `not network` marker |

**Confirmation:** Neither skipped test covers OCSP stapling, certificate-chain validation, TLS field extraction, silent-failure elimination, baseline integrity, or production correctness.

### 6. uv run python -m build
**Status:** PASS
**Output:** Successfully built trustlint-1.0.0.tar.gz and trustlint-1.0.0-py3-none-any.whl

### 7. git diff --check
**Status:** PASS
**Output:** No whitespace errors (only CRLF line-ending warnings on Windows)

### 8. TLS Probe Field Extraction
**Status:** PASS
**Result:** 24/24 tests passed in `tests/test_tls_probe.py`
**Fields verified:** `cipher_name`, `cipher_bits`, `compression`, `wildcard_cert`, `subject_alt_names`

### 9. CLI Smoke Tests
**Status:** PASS

| Command | Output |
|---------|--------|
| `trustlint --version` | trustlint v1.0.0 |
| `trustlint --list-classifications` | 20 registered TLS classifications |

### 10. Fixture-Backed Analysis Smoke Test
**Status:** PASS
**Test file:** `tests/test_cli_e2e_smoke.py`
**Result:** All golden fixture tests pass

## Architecture Review

### 1. Production Path Isolation
**Status:** PASS
- `trustlint.cli` does NOT import `trustlint.infrastructure.validation_runner`
- `trustlint.analyzer` does NOT import `trustlint.infrastructure.validation_runner`
- Only test file `tests/test_spl_decision_validation.py` imports validation_runner

### 2. validation_runner Offline Boundary
**Status:** PASS
- Module docstring explicitly states: "NOT intended for production ALLOW/DENY decisions"
- Module docstring explicitly states: "performs no network I/O and uses only in-memory message passing"
- Uses `MemoryKafkaAdapter` for in-memory processing only

### 3. Default Branch Integrity
**Status:** PASS
- master branch commit: cfd90b6 (unchanged)
- No direct or indirect default-branch changes

## Coverage Mapping

### Deleted Tests Audit
- **File:** `artifacts/PHASE1_COVERAGE_MAPPING.md`
- **Total deleted tests:** 13
- **Breakdown:**
  - `tests/test_sprint1_hardening.py`: 13 tests removed (TestBuildMixedReport: 5, TestCheckOcspStapled: 4, TestGetVerifiedChainCompat: 4)
  - `tests/test_sprint2_hardening.py`: 1 test removed (test_determine_chain_subtype_logs_exception), 2 restored (logger tests)
  - `tests/test_real_data_contract.py`: 0 tests removed (test_no_spl_v7_import_in_validation refactored, not deleted)
- **Retirement justification:** All deleted tests trace to functions/modules removed during package refactoring (`4a16af5`). No security behavior was silenced.

### TLS Probe Fields Restored
- **Fields:** `cipher_name`, `cipher_bits`, `compression`, `wildcard_cert`, `subject_alt_names`
- **Status:** RESTORED in `trustlint/infrastructure/tls_probe.py`
- **Tests:** `tests/test_tls_probe.py::TestHandshakeInfoDictNewFields` (2 tests verify defaults and extraction)

### Dependency Review
- **File:** `artifacts/DEPENDENCY_REVIEW.md`
- **Package:** httpx2 v2.5.0 (PyPI)
- **Reason:** starlette 1.3.1 TestClient requires httpx2
- **Status:** Correct dependency, well-maintained, permissive license (BSD-3-Clause)

## CI Run URLs

- **Last green CI:** https://github.com/Jonah15-sudo/trustlint/actions/runs/28459826477 (commit e668f40)
- **Status:** SUCCESS
- **Test Matrix:** Ubuntu and Windows, Python 3.10-3.13
- **Wheel Smoke:** Pass on Ubuntu and Windows
- **Note:** New commit required after TLS probe field restoration; CI will re-run on push

## Working Tree Status

```
M  .gitignore
M  artifacts/PHASE1_FAILURE_TRIAGE.md
M  artifacts/PHASE1_GATE.md
A  reports/local_real_validation/PHASE6_BASELINE_COMPARISON.md
M  tests/test_sprint2_hardening.py
M  tests/test_tls_policy_adapter.py
M  tests/test_tls_probe.py
M  trustlint/infrastructure/tls_probe.py
?? artifacts/DEPENDENCY_REVIEW.md
?? artifacts/PHASE1_COVERAGE_MAPPING.md
```

## Unresolved Risks

None. All Phase 1 gates are green.

## Verdict

**READY FOR CI** (not READY FOR MERGE)

All pre-push gates pass:
- uv lock consistent
- uv sync --frozen succeeds
- compileall clean
- pip check clean
- 823 passed, 2 skipped (neither covers OCSP/cert-chain/TLS-extraction/silent-fails/baseline/prod-correctness)
- 0 failures, 0 collection errors
- 54 subtests passed
- Wheel built successfully
- TLS probe: 24/24 passed
- CLI smoke: --version and --list-classifications pass
- git diff --check clean (no whitespace errors)
- Fixture-backed analysis smoke test passes
- Production path isolation confirmed
- Default branch integrity confirmed

**Awaiting:** CI re-run on push to confirm GitHub Actions green for the new commit.
