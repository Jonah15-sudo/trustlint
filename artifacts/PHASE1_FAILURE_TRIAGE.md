# TrustLint Phase 1 Failure Triage

## Failure Families

| # | Family | Test Files | Error/Failure Message | Reproduced on Master | Reproduced on PR #3 | Reproduced on PR #4 | Reproduced on Top Branch | Owning Component | Severity | Minimal Safe Fix | Coverage Proof |
|---|--------|------------|----------------------|---------------------|--------------------|--------------------|------------------------|------------------|----------|------------------|----------------|
| 1 | httpx2 missing | tests/security/test_dashboard_security.py (22 errors) | `RuntimeError: The starlette.testclient module requires the httpx2 package to be installed.` | Yes | Yes | Yes | Yes | test dependencies | demo-blocking | Add httpx2 to pyproject.toml dev dependencies (or verify httpx2 exists on PyPI; if not, pin starlette to version using httpx) | Tests remain and validate security headers once dependency is available |
| 2 | Entry point mismatch | tests/test_package_entry.py:73,82,256 | `AssertionError: 'trustlint.cli:main' != 'scripts.spl_tls_analyze:main'` | Yes | Yes | Yes | Yes | pyproject.toml / test assertions | release-blocking | Update 3 test assertions to expect `trustlint.cli:main` (matches pyproject.toml:39) | Tests still validate entry point is registered correctly |
| 3 | Golden snapshot drift - console | tests/test_cli_golden_acceptance.py:79 | `AssertionError: 'Domain: example.com\n  Decision: ALLOW\n...' != '====...'` | Yes | Yes | Yes | Yes | scripts/spl_tls_analyze.py (format_structured_text) | demo-blocking | Regenerate all 13 console fixtures using current format_structured_text output | Fixtures freeze current stable contract |
| 4 | Golden snapshot drift - JSON | tests/test_cli_golden_acceptance.py:96 | `AssertionError: '{\n    "tool": ..., "version": ...\n}' != '{\n    "tool": ..., "profile": ...\n}'` | Yes | Yes | Yes | Yes | scripts/spl_tls_analyze.py (format_json_output) | demo-blocking | Regenerate all 13 JSON fixtures using current format_json_output output | Fixtures freeze current stable contract |
| 5 | Golden snapshot drift - markdown | tests/test_cli_golden_acceptance.py:113 | `AssertionError: '# TrustLint Analysis Report\n...' != '# TLS Risk Analysis Report\n...'` | Yes | Yes | Yes | Yes | scripts/spl_tls_analyze.py (format_markdown_output) | demo-blocking | Regenerate all 13 markdown fixtures using current format_markdown_output output | Fixtures freeze current stable contract |
| 6 | Golden snapshot drift - batch | tests/test_cli_golden_acceptance.py:335,345,355 | `AssertionError: '=== BATCH SUMMARY ===\n...' != '\n=====...'` | Yes | Yes | Yes | Yes | scripts/spl_tls_analyze.py (format_batch_summary) | demo-blocking | Regenerate 3 batch fixtures (console, json, markdown) | Fixtures freeze current stable contract |
| 7 | Missing function _build_mixed_report | tests/test_sprint1_hardening.py:38,52,71,91 | `ImportError: cannot import name '_build_mixed_report' from 'scripts.run_local_tls_validation'` | Yes | Yes | Yes | Yes | scripts/run_local_tls_validation.py | deferred | Verify if function ever existed; if obsolete, remove tests with docstring; if needed, add to tls_probe.py and wrapper | Remove dead code tests, preserve coverage for active code |
| 8 | Missing function check_ocsp_stapled | tests/test_sprint1_hardening.py:229,239,246,256 | `ImportError: cannot import name 'check_ocsp_stapled' from 'scripts.ocsp_checker'` | Yes | Yes | Yes | Yes | scripts/ocsp_checker.py | deferred | Verify if function ever existed; if obsolete, remove tests with docstring; if needed, add to ocsp_checker.py | Remove dead code tests, preserve coverage for active code |
| 9 | Missing functions _get_issuer_spki, _parse_tbs | tests/test_sprint1_hardening.py:270,276,283 | `ImportError: cannot import name '_get_issuer_spki' from 'scripts.ocsp_checker'` | Yes | Yes | Yes | Yes | scripts/ocsp_checker.py | deferred | Verify if functions ever existed; if obsolete, remove tests with docstring | Remove dead code tests |
| 10 | Missing function _attempt_tls_handshake | tests/test_sprint1_hardening.py:295, tests/test_tls_probe.py:78,88 | `ImportError: cannot import name '_attempt_tls_handshake' from 'scripts.run_local_tls_validation'` | Yes | Yes | Yes | Yes | scripts/run_local_tls_validation.py (import * issue) | release-blocking | Add `__all__` to trustlint/infrastructure/tls_probe.py listing _attempt_tls_handshake and other needed functions, OR change wrapper to explicit import | Wrapper correctly re-exports needed functions |
| 11 | Missing function _determine_chain_subtype | tests/test_sprint2_hardening.py:116 | `ImportError: cannot import name '_determine_chain_subtype' from 'scripts.run_local_tls_validation'` | Yes | Yes | Yes | Yes | scripts/run_local_tls_validation.py (import * issue) | release-blocking | Add _determine_chain_subtype to tls_probe.py __all__ or explicit import in wrapper | Wrapper correctly re-exports needed functions |
| 12 | Health check mock issue | tests/test_sprint2_hardening.py:205 | `AssertionError: 0 != 1` | Yes | Yes | Yes | Yes | tests/test_sprint2_hardening.py | deferred | Fix mock to patch sys.version_info at the function's import location | Test properly validates health check behavior |
| 13 | Network test not marked | tests/test_tls_probe.py:114 | `AssertionError: dh2048.badssl.com should handshake successfully: CONNECTION_ERROR` | Yes | Yes | Yes | Yes | tests/test_tls_probe.py | deferred | Add @pytest.mark.network decorator to test_static_rsa_override | Test properly excluded from offline suite |
| 14 | Missing module validate_real_tls_data | tests/test_real_data_contract.py:149 | `ModuleNotFoundError: No module named 'scripts.validate_real_tls_data'` | Yes | Yes | Yes | Yes | scripts/validate_real_tls_data.py | deferred | Verify if module ever existed; if obsolete, remove the import and related test; if needed, create the module | Remove dead code test or restore module |

## Summary by Severity

### Release-blocking (must fix before merge)
- **#2**: Entry point mismatch (3 tests) - Update assertions to match pyproject.toml
- **#10**: Missing _attempt_tls_handshake (3 tests) - Fix import * issue
- **#11**: Missing _determine_chain_subtype (1 test) - Fix import * issue

### Demo-blocking (must fix for demo)
- **#1**: httpx2 missing (22 errors) - Add test dependency
- **#3-6**: Golden snapshot drift (9 tests) - Regenerate fixtures

### Deferred (can fix later)
- **#7**: Missing _build_mixed_report (5 tests) - Verify if obsolete
- **#8**: Missing check_ocsp_stapled (4 tests) - Verify if obsolete
- **#9**: Missing _get_issuer_spki, _parse_tbs (3 tests) - Verify if obsolete
- **#12**: Health check mock issue (1 test) - Fix mock target
- **#13**: Network test not marked (1 test) - Add pytest marker
- **#14**: Missing validate_real_tls_data module (1 test) - Verify if obsolete

## Fix Plan

1. **Immediate (release-blocking):**
   - Fix pyproject.toml entry point assertions
   - Fix tls_probe.py export list or wrapper imports

2. **Before demo (demo-blocking):**
   - Verify httpx2 package availability, add to dev deps
   - Regenerate all golden fixtures

3. **Follow-up (deferred):**
   - Audit each missing function to determine if it was deleted or never existed
   - Remove or restore functions accordingly
   - Fix health check mock
   - Mark network tests properly
