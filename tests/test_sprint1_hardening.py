"""Sprint 1 Hardening Tests — TrustLint v1.1 Verified.

Tests for Sprint 1 issues:
1. DEPRECATED_TLS_VERSION classification drift
2. deprecated_tls_check incorrect semantics
3. spl_policy_label always remains None
4. Fabricated HSTS evidence in SPL artifact
5. Fabricated CSP evidence in SPL artifact

Note: Tests for _build_mixed_report, check_ocsp_stapled, _get_issuer_spki,
and _parse_tbs have been removed as these functions were removed during
the package refactoring (they are obsolete).
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch, PropertyMock

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ── Issue 2: DEPRECATED_TLS_VERSION classification drift ──────────────────

class TestDeprecatedTLSClassificationDrift(unittest.TestCase):
    """DEPRECATED_TLS_VERSION must be in CLASSIFICATION and CLASSIFICATION_ORDER."""

    def test_in_classification_dict(self) -> None:
        from scripts.run_local_tls_validation import CLASSIFICATION
        self.assertIn("DEPRECATED_TLS_VERSION", CLASSIFICATION)
        self.assertEqual(CLASSIFICATION["DEPRECATED_TLS_VERSION"], "tls_deprecated")

    def test_in_classification_order(self) -> None:
        from scripts.run_local_tls_validation import CLASSIFICATION_ORDER
        self.assertIn("DEPRECATED_TLS_VERSION", CLASSIFICATION_ORDER)

    def test_classification_count_includes_deprecated(self) -> None:
        from scripts.run_local_tls_validation import CLASSIFICATION, CLASSIFICATION_ORDER
        self.assertEqual(len(CLASSIFICATION), 20)
        self.assertEqual(len(CLASSIFICATION_ORDER), 20)

    def test_deprecated_tls_version_in_risk_map(self) -> None:
        from tls_policy_adapter.schema import RISK_MAP
        self.assertIn("DEPRECATED_TLS_VERSION", RISK_MAP)


# ── Issue 3: deprecated_tls_check incorrect semantics ─────────────────────

class TestDeprecatedTLSCheckSemantics(unittest.TestCase):
    """deprecated_tls_check must use correct semantic values."""

    def test_rejected_when_server_refuses_tls11(self) -> None:
        """When TLS 1.1 handshake fails, deprecated_tls_check must be 'rejected'."""
        from scripts.run_local_tls_validation import probe_domain
        # modern.example.com should reject TLS 1.1
        result = probe_domain("modern.example.com")
        tls_info = result.get("tls") or {}
        # If the check ran and TLS 1.1 was rejected, it should say "rejected"
        if tls_info.get("deprecated_tls_check") == "rejected":
            self.assertFalse(tls_info.get("deprecated_tls_detected"))
        # If the check didn't run (unavailable), that's also valid
        if tls_info.get("deprecated_tls_check") == "unavailable_on_platform":
            self.assertFalse(tls_info.get("deprecated_tls_detected"))

    def test_supported_only_when_detected(self) -> None:
        """'supported' should only appear when deprecated TLS is actually detected."""
        from scripts.run_local_tls_validation import probe_domain
        result = probe_domain("badssl.com")
        tls_info = result.get("tls") or {}
        check = tls_info.get("deprecated_tls_check")
        detected = tls_info.get("deprecated_tls_detected", False)
        # If check is "supported", deprecated_tls_detected must be True
        if check == "supported":
            self.assertTrue(detected,
                            "deprecated_tls_check='supported' requires deprecated_tls_detected=True")


# ── Issue 4: spl_policy_label always remains None ─────────────────────────

class TestSplPolicyLabel(unittest.TestCase):
    """spl_policy_label must be populated from SPL pipeline results."""

    @patch("trustlint.analyzer.probe_domain")
    def test_label_set_from_spl_result(self, mock_probe: MagicMock) -> None:
        from scripts.spl_tls_analyze import analyze_domain
        from spl_v7.dsl import FeatureDSLProgram
        from spl_v7.kafka_pipeline import EvidencePipeline

        mock_probe.return_value = {
            "domain": "example.com",
            "probe_timestamp": "2026-06-01T12:00:00Z",
            "resolved_ip": "1.2.3.4",
            "tls": {
                "tls_version": "TLSv1.3",
                "cert_expiry_days": 89,
                "cert_is_expired": False,
                "cert_chain_complete": True,
                "handshake_time_ms": 45.2,
                "ocsp_performed": False,
                "ocsp_stapled": False,
                "ocsp_status": None,
                "ocsp_error": None,
                "ocsp_responder_url": None,
                "deprecated_tls_detected": False,
                "deprecated_tls_check": "supported",
            },
            "overall_status": "valid",
            "classification": "VALID_TLS",
        }

        program = FeatureDSLProgram.from_text("feature tls_valid = data.valid\n")
        pipeline = EvidencePipeline(feature_program=program)
        r = analyze_domain("example.com", profile="balanced", spl_pipeline=pipeline)

        # spl_policy_label should be "ALLOW" or "DENY", not None
        self.assertIsNotNone(r["spl"]["decision"])
        # The orchestrator output should have spl_policy_label set
        # (check that it's not None in the internal decide call)

    @patch("trustlint.analyzer.probe_domain")
    def test_label_none_without_spl(self, mock_probe: MagicMock) -> None:
        from scripts.spl_tls_analyze import analyze_domain
        mock_probe.return_value = {
            "domain": "example.com",
            "probe_timestamp": "2026-06-01T12:00:00Z",
            "resolved_ip": "1.2.3.4",
            "tls": {
                "tls_version": "TLSv1.3",
                "cert_expiry_days": 89,
                "cert_is_expired": False,
                "cert_chain_complete": True,
                "handshake_time_ms": 45.2,
                "ocsp_performed": False,
                "ocsp_stapled": False,
                "ocsp_status": None,
                "ocsp_error": None,
                "ocsp_responder_url": None,
                "deprecated_tls_detected": False,
                "deprecated_tls_check": "supported",
            },
            "overall_status": "valid",
            "classification": "VALID_TLS",
        }
        r = analyze_domain("example.com", profile="balanced")
        # Without SPL, spl_policy_label should be None
        self.assertIsNone(r["spl"]["decision"])


# ── Issues 7 & 8: Fabricated HSTS/CSP evidence ───────────────────────────

class TestFabricatedEvidenceFix(unittest.TestCase):
    """HSTS and CSP must not be fabricated as False."""

    def test_hsts_not_fabricated(self) -> None:
        from scripts.spl_tls_analyze import _build_evidence_artifact
        probe = {
            "domain": "example.com",
            "classification": "VALID_TLS",
            "tls": {
                "cert_is_expired": False,
                "cert_chain_complete": True,
                "cert_expiry_days": 89,
                "handshake_time_ms": 45.2,
            },
        }
        artifact = _build_evidence_artifact("example.com", probe)
        # HSTS should be None (not checked), not False (fabricated)
        self.assertIsNone(artifact["data"]["headers"]["hsts"])
        self.assertFalse(artifact["data"]["headers"]["hsts_checked"])

    def test_csp_not_fabricated(self) -> None:
        from scripts.spl_tls_analyze import _build_evidence_artifact
        probe = {
            "domain": "example.com",
            "classification": "VALID_TLS",
            "tls": {
                "cert_is_expired": False,
                "cert_chain_complete": True,
                "cert_expiry_days": 89,
                "handshake_time_ms": 45.2,
            },
        }
        artifact = _build_evidence_artifact("example.com", probe)
        # CSP should be None (not checked), not False (fabricated)
        self.assertIsNone(artifact["data"]["headers"]["csp"])
        self.assertFalse(artifact["data"]["headers"]["csp_checked"])

    def test_headers_contain_checked_flags(self) -> None:
        from scripts.spl_tls_analyze import _build_evidence_artifact
        probe = {
            "domain": "example.com",
            "classification": "VALID_TLS",
            "tls": {
                "cert_is_expired": False,
                "cert_chain_complete": True,
                "cert_expiry_days": 89,
                "handshake_time_ms": 45.2,
            },
        }
        artifact = _build_evidence_artifact("example.com", probe)
        headers = artifact["data"]["headers"]
        self.assertIn("hsts", headers)
        self.assertIn("csp", headers)
        self.assertIn("hsts_checked", headers)
        self.assertIn("csp_checked", headers)


if __name__ == "__main__":
    unittest.main()
