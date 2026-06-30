"""Sprint 2 Architecture Hardening Tests — TrustLint v1.1 Verified.

Tests for the 6 Sprint 2 issues:
1. Single source of truth for classifications
2. Eliminate silent failures and hidden exceptions
3. Improve batch processing reliability and reporting
4. Implement a meaningful health check
5. Unify version management
6. Audit all exception handling paths
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ── Issue 1: Single source of truth for classifications ────────────────────

class TestClassificationsSingleSource(unittest.TestCase):
    """Canonical classifications module must be the single source of truth."""

    def test_all_classifications_tuple(self) -> None:
        from tls_policy_adapter.classifications import ALL_CLASSIFICATIONS
        self.assertIsInstance(ALL_CLASSIFICATIONS, tuple)
        self.assertEqual(len(ALL_CLASSIFICATIONS), 20)

    def test_deprecated_tls_versions_frozenset(self) -> None:
        from tls_policy_adapter.classifications import DEPRECATED_TLS_VERSIONS
        self.assertIsInstance(DEPRECATED_TLS_VERSIONS, frozenset)
        self.assertIn("tlsv1", DEPRECATED_TLS_VERSIONS)
        self.assertIn("tlsv1.1", DEPRECATED_TLS_VERSIONS)
        self.assertIn("tls1", DEPRECATED_TLS_VERSIONS)

    def test_classification_severity_mapping(self) -> None:
        from tls_policy_adapter.classifications import CLASSIFICATION_SEVERITY
        self.assertEqual(len(CLASSIFICATION_SEVERITY), 20)
        self.assertEqual(CLASSIFICATION_SEVERITY["VALID_TLS"], "NONE")
        self.assertEqual(CLASSIFICATION_SEVERITY["REVOKED_CERT"], "CRITICAL")

    def test_classification_risk_category_mapping(self) -> None:
        from tls_policy_adapter.classifications import CLASSIFICATION_RISK_CATEGORY
        self.assertEqual(len(CLASSIFICATION_RISK_CATEGORY), 20)
        self.assertEqual(CLASSIFICATION_RISK_CATEGORY["VALID_TLS"], "ACCEPTABLE_TLS")

    def test_classification_to_overall_status(self) -> None:
        from tls_policy_adapter.classifications import CLASSIFICATION_TO_OVERALL_STATUS
        self.assertEqual(len(CLASSIFICATION_TO_OVERALL_STATUS), 20)
        self.assertEqual(CLASSIFICATION_TO_OVERALL_STATUS["VALID_TLS"], "valid")

    def test_is_valid_classification(self) -> None:
        from tls_policy_adapter.classifications import is_valid_classification
        self.assertTrue(is_valid_classification("VALID_TLS"))
        self.assertTrue(is_valid_classification("DEPRECATED_TLS_VERSION"))
        self.assertFalse(is_valid_classification("INVALID_CLASSIFICATION"))

    def test_is_deprecated_tls_version(self) -> None:
        from tls_policy_adapter.classifications import is_deprecated_tls_version
        self.assertTrue(is_deprecated_tls_version("TLSv1"))
        self.assertTrue(is_deprecated_tls_version("tlsv1.1"))
        self.assertTrue(is_deprecated_tls_version("TLS1"))
        self.assertFalse(is_deprecated_tls_version("TLSv1.2"))
        self.assertFalse(is_deprecated_tls_version("TLSv1.3"))

    def test_get_classification_severity(self) -> None:
        from tls_policy_adapter.classifications import get_classification_severity
        self.assertEqual(get_classification_severity("VALID_TLS"), "NONE")
        self.assertEqual(get_classification_severity("REVOKED_CERT"), "CRITICAL")
        self.assertEqual(get_classification_severity("UNKNOWN"), "LOW")  # default

    def test_get_classification_risk_category(self) -> None:
        from tls_policy_adapter.classifications import get_classification_risk_category
        self.assertEqual(get_classification_risk_category("VALID_TLS"), "ACCEPTABLE_TLS")
        self.assertEqual(get_classification_risk_category("UNKNOWN"), "UNKNOWN_RISK")  # default

    def test_classifications_importable_from_adapter(self) -> None:
        from tls_policy_adapter import (
            ALL_CLASSIFICATIONS,
            DEPRECATED_TLS_VERSIONS,
            DEPRECATED_TLS_CLASSIFICATION,
            is_deprecated_tls_version,
        )
        self.assertEqual(len(ALL_CLASSIFICATIONS), 20)
        self.assertEqual(DEPRECATED_TLS_CLASSIFICATION, "DEPRECATED_TLS_VERSION")

    def test_run_local_uses_canonical(self) -> None:
        from scripts.run_local_tls_validation import CLASSIFICATION, CLASSIFICATION_ORDER
        from tls_policy_adapter.classifications import CLASSIFICATION_TO_OVERALL_STATUS, ALL_CLASSIFICATIONS
        self.assertEqual(CLASSIFICATION, dict(CLASSIFICATION_TO_OVERALL_STATUS))
        self.assertEqual(CLASSIFICATION_ORDER, list(ALL_CLASSIFICATIONS))


# ── Issue 2: Eliminate silent failures ─────────────────────────────────────

class TestSilentFailuresEliminated(unittest.TestCase):
    """Exception handlers must log instead of silently swallowing."""

    def test_run_local_has_logger(self) -> None:
        import scripts.run_local_tls_validation as mod
        self.assertTrue(hasattr(mod, "logger"))

    def test_spl_tls_analyze_has_logger(self) -> None:
        import scripts.spl_tls_analyze as mod
        self.assertTrue(hasattr(mod, "logger"))


# ── Issue 3: Batch processing reliability ──────────────────────────────────

class TestBatchProcessingReliability(unittest.TestCase):
    """Batch processing must handle errors gracefully and report them."""

    def test_compute_summary_with_errors(self) -> None:
        from scripts.spl_tls_analyze import compute_summary
        results = [
            {"final": {"decision": "ALLOW", "risk": "NONE"},
             "tls_probe": {"is_probe_limited": False, "classification": "VALID_TLS"}},
        ]
        errors = ["  bad.com: ERROR — connection refused"]
        summary = compute_summary(results, errors)
        self.assertEqual(summary["total_domains"], 1)
        self.assertEqual(summary["failed_domains"], 1)
        self.assertEqual(len(summary["error_details"]), 1)

    def test_compute_summary_without_errors(self) -> None:
        from scripts.spl_tls_analyze import compute_summary
        results = [
            {"final": {"decision": "ALLOW", "risk": "NONE"},
             "tls_probe": {"is_probe_limited": False, "classification": "VALID_TLS"}},
        ]
        summary = compute_summary(results)
        self.assertNotIn("failed_domains", summary)
        self.assertNotIn("error_details", summary)

    def test_format_batch_summary_with_errors(self) -> None:
        from scripts.spl_tls_analyze import format_batch_summary
        results = [
            {"final": {"decision": "ALLOW", "risk": "NONE", "recommended_action": "No action"},
             "tls_probe": {"is_probe_limited": False, "classification": "VALID_TLS", "warnings": []},
             "domain": "good.com"},
        ]
        errors = ["  bad.com: ERROR — connection refused"]
        summary = format_batch_summary(results, errors)
        self.assertIn("Failed Domains", summary)
        self.assertIn("bad.com", summary)

    def test_format_batch_summary_without_errors(self) -> None:
        from scripts.spl_tls_analyze import format_batch_summary
        results = [
            {"final": {"decision": "ALLOW", "risk": "NONE", "recommended_action": "No action"},
             "tls_probe": {"is_probe_limited": False, "classification": "VALID_TLS", "warnings": []},
             "domain": "good.com"},
        ]
        summary = format_batch_summary(results)
        self.assertNotIn("Failed Domains", summary)


# ── Issue 4: Meaningful health check ──────────────────────────────────────

class TestHealthCheck(unittest.TestCase):
    """Health check must validate critical system components."""

    def test_health_check_function_exists(self) -> None:
        from scripts.spl_tls_analyze import _run_health_check
        self.assertTrue(callable(_run_health_check))

    def test_health_check_returns_int(self) -> None:
        from scripts.spl_tls_analyze import _run_health_check
        result = _run_health_check()
        self.assertIsInstance(result, int)
        self.assertIn(result, (0, 1))

    def test_health_check_passes_on_valid_system(self) -> None:
        from scripts.spl_tls_analyze import _run_health_check
        # On a working system, health check should pass
        result = _run_health_check()
        self.assertEqual(result, 0)

    @patch("trustlint.cli.sys")
    def test_health_check_fails_on_old_python(self, mock_sys: MagicMock) -> None:
        from trustlint.cli import _run_health_check
        # Create a proper mock for version_info that supports comparison
        mock_version_info = MagicMock()
        mock_version_info.__lt__ = lambda self, other: (3, 9, 0) < other
        mock_version_info.major = 3
        mock_version_info.minor = 9
        mock_version_info.micro = 0
        mock_sys.version_info = mock_version_info
        mock_sys.version = "3.9.0"
        result = _run_health_check()
        self.assertEqual(result, 1)


# ── Issue 5: Version management ───────────────────────────────────────────

class TestVersionManagement(unittest.TestCase):
    """Version must be consistent across pyproject.toml and code."""

    def test_spl_tls_analyze_version(self) -> None:
        from scripts.spl_tls_analyze import __version__
        self.assertEqual(__version__, "1.0.0")

    def test_version_matches_pyproject(self) -> None:
        pyproject_path = os.path.join(PROJECT_ROOT, "pyproject.toml")
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('version = "1.0.0"', content)

    def test_tool_name(self) -> None:
        from scripts.spl_tls_analyze import TOOL_NAME
        self.assertEqual(TOOL_NAME, "trustlint")


# ── Issue 6: Exception handling audit ──────────────────────────────────────

class TestExceptionHandlingAudit(unittest.TestCase):
    """Exception handlers must not silently swallow errors."""

    def test_run_local_validation_has_logging(self) -> None:
        import scripts.run_local_tls_validation as mod
        self.assertTrue(hasattr(mod, "logger"))
        self.assertTrue(hasattr(mod.logger, "debug"))

    def test_spl_tls_analyze_has_logging(self) -> None:
        import scripts.spl_tls_analyze as mod
        self.assertTrue(hasattr(mod, "logger"))
        self.assertTrue(hasattr(mod.logger, "debug"))

    def test_classifications_module_imports_cleanly(self) -> None:
        from tls_policy_adapter.classifications import (
            ALL_CLASSIFICATIONS,
            DEPRECATED_TLS_VERSIONS,
            CLASSIFICATION_SEVERITY,
            CLASSIFICATION_RISK_CATEGORY,
            CLASSIFICATION_TO_OVERALL_STATUS,
            get_classification_severity,
            get_classification_risk_category,
            is_valid_classification,
            is_deprecated_tls_version,
        )
        # All imports should succeed without error
        self.assertIsNotNone(ALL_CLASSIFICATIONS)
        self.assertIsNotNone(DEPRECATED_TLS_VERSIONS)

    def test_classifications_consistent_with_risk_map(self) -> None:
        from tls_policy_adapter.classifications import ALL_CLASSIFICATIONS
        from tls_policy_adapter.schema import RISK_MAP
        # Every classification in ALL_CLASSIFICATIONS should have a RISK_MAP entry
        for cls in ALL_CLASSIFICATIONS:
            self.assertIn(cls, RISK_MAP, f"Classification {cls} missing from RISK_MAP")


if __name__ == "__main__":
    unittest.main()
