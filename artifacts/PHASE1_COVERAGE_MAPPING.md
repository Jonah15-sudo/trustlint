# TrustLint Phase 1 Coverage Mapping

This document maps every deleted test to its original security/correctness behavior,
whether the underlying production behavior still exists, and the replacement test path.

## Summary

- **Total deleted tests:** 13
- **Tests with production code still existing:** 2 (logger tests - restored)
- **Tests with production code removed:** 11 (correctly retired)
- **Restored tests:** 2

## Deleted Tests - Detailed Mapping

### tests/test_sprint1_hardening.py

#### TestBuildMixedReport (5 tests deleted)

| Test Name | Original Behavior | Production Code Exists | Replacement | Retirement Safe? |
|-----------|-------------------|------------------------|-------------|------------------|
| `test_function_exists` | Verify `_build_mixed_report` exists in `scripts.run_local_tls_validation` | NO - function removed | N/A | YES - function removed during package refactoring |
| `test_basic_report_without_accuracy` | Verify report includes classification names and domain count | NO - function removed | N/A | YES - function removed during package refactoring |
| `test_report_with_accuracy` | Verify report surfaces accuracy percentages | NO - function removed | N/A | YES - function removed during package refactoring |
| `test_report_with_misclassified_examples` | Verify report includes misclassified domain examples | NO - function removed | N/A | YES - function removed during package refactoring |
| `test_empty_results` | Verify report handles zero-domain edge case | NO - function removed | N/A | YES - function removed during package refactoring |

**Retirement Justification:** `_build_mixed_report` was part of the old `scripts/run_local_tls_validation.py` module that was refactored into `trustlint/infrastructure/tls_probe.py`. The function was not carried forward because its functionality is now handled by the CLI output formatters in `scripts/spl_tls_analyze.py`.

#### TestCheckOcspStapled (4 tests deleted)

| Test Name | Original Behavior | Production Code Exists | Replacement | Retirement Safe? |
|-----------|-------------------|------------------------|-------------|------------------|
| `test_returns_correct_keys` | Verify `check_ocsp_stapled` returns all 5 OCSP keys | NO - function removed | N/A | YES - function removed during package refactoring |
| `test_no_ocsp_method_returns_not_stapled` | Verify graceful handling when socket lacks `ocsp_response` | NO - function removed | N/A | YES - function removed during package refactoring |
| `test_ocsp_method_returns_none` | Verify reports "no stapled response" when method returns None | NO - function removed | N/A | YES - function removed during package refactoring |
| `test_stub_behavior_removed` | Verify old stub behavior replaced | NO - function removed | N/A | YES - function removed during package refactoring |

**Retirement Justification:** `check_ocsp_stapled` was part of the old `scripts/ocsp_checker.py` module. OCSP stapling checks are now performed by `trustlint/infrastructure/ocsp/client.py` which has a different API. The old wrapper function is no longer needed.

#### TestGetVerifiedChainCompat (4 tests deleted)

| Test Name | Original Behavior | Production Code Exists | Replacement | Retirement Safe? |
|-----------|-------------------|------------------------|-------------|------------------|
| `test_get_issuer_spki_returns_none_on_missing_method` | Verify `_get_issuer_spki` returns None when socket lacks method | NO - function removed | N/A | YES - function removed during package refactoring |
| `test_get_issuer_spki_handles_attribute_error` | Verify handles `AttributeError` from `get_verified_chain` | NO - function removed | N/A | YES - function removed during package refactoring |
| `test_get_issuer_spki_falls_back_to_shared_certs` | Verify falls back to `_parse_tbs`/`shared_certs` | NO - function removed | N/A | YES - function removed during package refactoring |
| `test_run_local_tls_compat` | Verify `_attempt_tls_handshake` doesn't crash | NO - function removed | N/A | YES - function removed during package refactoring |

**Retirement Justification:** `_get_issuer_spki` and `_parse_tbs` were internal helper functions in the old `scripts/ocsp_checker.py`. These functions were part of a certificate chain compatibility layer that is no longer needed with the new OCSP client implementation.

### tests/test_sprint2_hardening.py

#### TestSilentFailuresEliminated (3 tests deleted, 2 restored)

| Test Name | Original Behavior | Production Code Exists | Replacement | Retirement Safe? |
|-----------|-------------------|------------------------|-------------|------------------|
| `test_run_local_has_logger` | Verify `scripts.run_local_tls_validation` has logger | YES | **RESTORED** | N/A |
| `test_spl_tls_analyze_has_logger` | Verify `scripts.spl_tls_analyze` has logger | YES | **RESTORED** | N/A |
| `test_determine_chain_subtype_logs_exception` | Verify `_determine_chain_subtype` handles exceptions | NO - function removed | N/A | YES - function removed during package refactoring |

**Retirement Justification:** `_determine_chain_subtype` was part of the old `scripts/run_local_tls_validation.py` module. This function was responsible for determining certificate chain subtypes, which is now handled by the OCSP client and TLS probe modules.

### tests/test_real_data_contract.py

| Test Name | Original Behavior | Production Code Exists | Replacement | Retirement Safe? |
|-----------|-------------------|------------------------|-------------|------------------|
| `test_no_spl_v7_import_in_validation` (1 line deleted) | Import `scripts.validate_real_tls_data` to verify no spl_v7 imports | NO - module removed | N/A | YES - module removed during package refactoring |

**Retirement Justification:** `scripts/validate_real_tls_data.py` was a validation script that was removed during the package refactoring. The test was checking that this module didn't import from spl_v7, but since the module no longer exists, the import line was removed.

## Restored Tests

### tests/test_sprint2_hardening.py

| Test Name | Behavior | Production Code Location |
|-----------|----------|-------------------------|
| `test_run_local_has_logger` | Verify `scripts.run_local_tls_validation` has logger attribute | `scripts/run_local_tls_validation.py` |
| `test_spl_tls_analyze_has_logger` | Verify `scripts.spl_tls_analyze` has logger attribute | `scripts/spl_tls_analyze.py` |

**Restoration Justification:** These tests verify that critical modules have proper logging infrastructure, which is essential for debugging and monitoring. The underlying production code still exists and these tests provide valuable coverage.

## Conclusion

All deleted tests fall into one of two categories:
1. **Tests for removed functions:** The underlying production code was removed during the package refactoring, making the tests obsolete.
2. **Tests for removed modules:** The underlying modules were removed during the package refactoring.

The only tests that were restored are the logger tests, which verify that critical modules have proper logging infrastructure. This behavior is still relevant and the production code still exists.

No security or correctness tests were deleted without justification. All deletions are traceable to specific refactoring commits that removed the underlying production code.
