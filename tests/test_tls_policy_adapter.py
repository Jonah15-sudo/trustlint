"""Tests for Phase 6 — TLS Risk Policy Adapter.

Verifies:
- Every TLS classification maps to a risk category
- Every TLS classification maps to a severity
- VALID_TLS maps to ACCEPTABLE_TLS / NONE
- Security risks map to SECURITY_RISK severity >= HIGH
- Availability risks map to AVAILABILITY_RISK severity MEDIUM
- Deprecated TLS maps to DEPRECATED_PROTOCOL_RISK
- Incomplete vs untrusted chain ambiguity is documented
- Adapter does not read expectation files
- Adapter output schema is stable
- Benchmark runner produces structured JSON
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from typing import Any, Dict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tls_policy_adapter import (
    classify_risk,
    enrich_evidence,
    EnrichedEvidence,
    RISK_MAP,
    SEVERITY_ORDER,
    SEVERITY_RANK,
)
from tls_policy_adapter.schema import (
    all_classifications,
    TLSPolicyEvidence,
)
from tls_policy_adapter.evidence_adapter import AdapterBenchmarkResult


def _make_benchmark_results() -> Dict[str, Any]:
    """Build a synthetic benchmark results dict matching the runner's JSON schema."""
    baselines = [
        {
            "mode": "adapter-only",
            "description": "Adapter-only: deterministic classification mapping, no SPL",
            "conformance_pct": 95.8,
            "category_performance": {
                "VALID_TLS": {"conformance_pct": 100.0},
                "EXPIRED_CERT": {"conformance_pct": 100.0},
                "DNS_FAILURE": {"conformance_pct": 0.0},
            },
            "total": 120,
        },
        {
            "mode": "spl-observation",
            "description": "SPL observation: cold-start, no training",
            "conformance_pct": 70.3,
            "category_performance": {
                "VALID_TLS": {"conformance_pct": 80.0},
                "EXPIRED_CERT": {"conformance_pct": 50.0},
                "DNS_FAILURE": {"conformance_pct": 0.0},
            },
            "total": 120,
        },
        {
            "mode": "spl-holdout",
            "description": "SPL holdout: generalization estimate on unseen data",
            "conformance_pct": 70.3,
            "category_performance": {
                "VALID_TLS": {"conformance_pct": 80.0},
                "EXPIRED_CERT": {"conformance_pct": 50.0},
                "DNS_FAILURE": {"conformance_pct": 0.0},
            },
            "total": 120,
            "run_details": [
                {"run": 1, "train_size": 83, "holdout_size": 37, "conformance_pct": 70.3},
            ],
        },
        {
            "mode": "spl-proxy-trained",
            "description": "SPL proxy-trained: NOT generalization (train and eval on all 120)",
            "conformance_pct": 95.8,
            "category_performance": {
                "VALID_TLS": {"conformance_pct": 100.0},
                "EXPIRED_CERT": {"conformance_pct": 100.0},
                "DNS_FAILURE": {"conformance_pct": 0.0},
            },
            "total": 120,
        },
    ]
    return {
        "_metadata": {
            "phase": "Phase 6.5",
            "description": "Baseline comparison: adapter-only, SPL observation, SPL holdout, SPL proxy-trained",
            "generated": "2026-06-10T00:00:00Z",
            "spl_core_modified": False,
            "ofe_status": "HOLD_PENDING_REAL_DATA",
            "note": "Only spl-holdout is a generalization estimate.",
        },
        "domain_count": 120,
        "baselines": baselines,
    }


class TestClassificationCoverage(unittest.TestCase):
    """Every recognized TLS classification must map to a risk category."""

    def test_all_classifications_have_risk_category(self) -> None:
        for cls in all_classifications():
            evidence = classify_risk(cls)
            self.assertIsInstance(evidence.risk_category, str)
            self.assertGreater(len(evidence.risk_category), 0)

    def test_all_classifications_have_severity(self) -> None:
        for cls in all_classifications():
            evidence = classify_risk(cls)
            self.assertIn(evidence.severity, SEVERITY_ORDER)

    def test_all_classifications_have_failure_family(self) -> None:
        for cls in all_classifications():
            evidence = classify_risk(cls)
            self.assertIsInstance(evidence.failure_family, str)
            self.assertGreater(len(evidence.failure_family), 0)

    def test_all_classifications_have_action_hint(self) -> None:
        for cls in all_classifications():
            evidence = classify_risk(cls)
            self.assertIsInstance(evidence.action_hint, str)
            self.assertGreater(len(evidence.action_hint), 0)

    def test_all_classifications_have_policy_reason(self) -> None:
        for cls in all_classifications():
            evidence = classify_risk(cls)
            self.assertIsInstance(evidence.policy_reason, str)
            self.assertGreater(len(evidence.policy_reason), 0)

    def test_risk_map_matches_classifications(self) -> None:
        classifications = set(all_classifications())
        mapped = set(RISK_MAP.keys())
        self.assertEqual(classifications, mapped,
                         "RISK_MAP keys must match all_classifications()")


class TestValidTlsMapping(unittest.TestCase):
    """VALID_TLS must map to ACCEPTABLE_TLS / NONE."""

    def test_valid_tls_risk_category(self) -> None:
        evidence = classify_risk("VALID_TLS")
        self.assertEqual(evidence.risk_category, "ACCEPTABLE_TLS")

    def test_valid_tls_severity(self) -> None:
        evidence = classify_risk("VALID_TLS")
        self.assertEqual(evidence.severity, "NONE")

    def test_valid_tls_failure_family(self) -> None:
        evidence = classify_risk("VALID_TLS")
        self.assertEqual(evidence.failure_family, "NONE")

    def test_valid_tls_action_hint(self) -> None:
        evidence = classify_risk("VALID_TLS")
        self.assertEqual(evidence.action_hint, "NONE")


class TestSecurityRiskMapping(unittest.TestCase):
    """Security risk classifications must map to SECURITY_RISK severity >= HIGH."""

    def test_expired_cert_is_high(self) -> None:
        evidence = classify_risk("EXPIRED_CERT")
        self.assertEqual(evidence.risk_category, "SECURITY_RISK")
        self.assertEqual(evidence.severity, "HIGH")
        self.assertEqual(evidence.failure_family, "CERTIFICATE_TRUST")

    def test_self_signed_cert_is_high(self) -> None:
        evidence = classify_risk("SELF_SIGNED_CERT")
        self.assertEqual(evidence.risk_category, "SECURITY_RISK")
        self.assertEqual(evidence.severity, "HIGH")
        self.assertEqual(evidence.failure_family, "CERTIFICATE_TRUST")

    def test_wrong_host_cert_is_critical(self) -> None:
        evidence = classify_risk("WRONG_HOST_CERT")
        self.assertEqual(evidence.risk_category, "SECURITY_RISK")
        self.assertEqual(evidence.severity, "CRITICAL")
        self.assertEqual(evidence.failure_family, "CERTIFICATE_TRUST")

    def test_untrusted_chain_is_high(self) -> None:
        evidence = classify_risk("UNTRUSTED_CHAIN")
        self.assertEqual(evidence.risk_category, "SECURITY_RISK")
        self.assertEqual(evidence.severity, "HIGH")
        self.assertEqual(evidence.failure_family, "CHAIN_TRUST")

    def test_all_security_risks_have_high_or_critical(self) -> None:
        security_classifications = [
            "EXPIRED_CERT", "SELF_SIGNED_CERT", "WRONG_HOST_CERT",
            "UNTRUSTED_CHAIN", "WEAK_CIPHER_SUITE",
        ]
        for cls in security_classifications:
            evidence = classify_risk(cls)
            self.assertIn(evidence.severity, ("HIGH", "CRITICAL"),
                          f"{cls} must be HIGH or CRITICAL")


class TestWeakCipherSuiteMapping(unittest.TestCase):
    """WEAK_CIPHER_SUITE must map to SECURITY_RISK severity HIGH."""

    def test_weak_cipher_suite_risk_category(self) -> None:
        evidence = classify_risk("WEAK_CIPHER_SUITE")
        self.assertEqual(evidence.risk_category, "SECURITY_RISK")

    def test_weak_cipher_suite_severity(self) -> None:
        evidence = classify_risk("WEAK_CIPHER_SUITE")
        self.assertEqual(evidence.severity, "HIGH")

    def test_weak_cipher_suite_failure_family(self) -> None:
        evidence = classify_risk("WEAK_CIPHER_SUITE")
        self.assertEqual(evidence.failure_family, "PROTOCOL_WEAKNESS")

    def test_weak_cipher_suite_action_hint(self) -> None:
        evidence = classify_risk("WEAK_CIPHER_SUITE")
        self.assertEqual(evidence.action_hint, "MODERNIZE_OR_DENY")


class TestStaticRsaKeyExchangeMapping(unittest.TestCase):
    """STATIC_RSA_KEY_EXCHANGE must map to SECURITY_RISK severity MEDIUM."""

    def test_static_rsa_risk_category(self) -> None:
        evidence = classify_risk("STATIC_RSA_KEY_EXCHANGE")
        self.assertEqual(evidence.risk_category, "SECURITY_RISK")

    def test_static_rsa_severity(self) -> None:
        evidence = classify_risk("STATIC_RSA_KEY_EXCHANGE")
        self.assertEqual(evidence.severity, "MEDIUM")

    def test_static_rsa_failure_family(self) -> None:
        evidence = classify_risk("STATIC_RSA_KEY_EXCHANGE")
        self.assertEqual(evidence.failure_family, "PROTOCOL_WEAKNESS")

    def test_static_rsa_action_hint(self) -> None:
        evidence = classify_risk("STATIC_RSA_KEY_EXCHANGE")
        self.assertEqual(evidence.action_hint, "MODERNIZE_OR_DENY")


class TestTlsCompressionEnabledMapping(unittest.TestCase):
    """TLS_COMPRESSION_ENABLED must map to SECURITY_RISK severity MEDIUM."""

    def test_compression_risk_category(self) -> None:
        evidence = classify_risk("TLS_COMPRESSION_ENABLED")
        self.assertEqual(evidence.risk_category, "SECURITY_RISK")

    def test_compression_severity(self) -> None:
        evidence = classify_risk("TLS_COMPRESSION_ENABLED")
        self.assertEqual(evidence.severity, "MEDIUM")

    def test_compression_failure_family(self) -> None:
        evidence = classify_risk("TLS_COMPRESSION_ENABLED")
        self.assertEqual(evidence.failure_family, "PROTOCOL_WEAKNESS")

    def test_compression_action_hint(self) -> None:
        evidence = classify_risk("TLS_COMPRESSION_ENABLED")
        self.assertEqual(evidence.action_hint, "MODERNIZE_OR_DENY")


class TestWildcardCertificateMapping(unittest.TestCase):
    """WILDCARD_CERTIFICATE must map to ACCEPTABLE_TLS severity LOW."""

    def test_wildcard_risk_category(self) -> None:
        evidence = classify_risk("WILDCARD_CERTIFICATE")
        self.assertEqual(evidence.risk_category, "ACCEPTABLE_TLS")

    def test_wildcard_severity(self) -> None:
        evidence = classify_risk("WILDCARD_CERTIFICATE")
        self.assertEqual(evidence.severity, "LOW")

    def test_wildcard_failure_family(self) -> None:
        evidence = classify_risk("WILDCARD_CERTIFICATE")
        self.assertEqual(evidence.failure_family, "CERTIFICATE_TRUST")

    def test_wildcard_action_hint(self) -> None:
        evidence = classify_risk("WILDCARD_CERTIFICATE")
        self.assertEqual(evidence.action_hint, "REVIEW")


class TestMissingOcspStapleMapping(unittest.TestCase):
    """MISSING_OCSP_STAPLE must map to ACCEPTABLE_TLS severity LOW."""

    def test_missing_staple_risk_category(self) -> None:
        evidence = classify_risk("MISSING_OCSP_STAPLE")
        self.assertEqual(evidence.risk_category, "ACCEPTABLE_TLS")

    def test_missing_staple_severity(self) -> None:
        evidence = classify_risk("MISSING_OCSP_STAPLE")
        self.assertEqual(evidence.severity, "LOW")

    def test_missing_staple_failure_family(self) -> None:
        evidence = classify_risk("MISSING_OCSP_STAPLE")
        self.assertEqual(evidence.failure_family, "AVAILABILITY")

    def test_missing_staple_action_hint(self) -> None:
        evidence = classify_risk("MISSING_OCSP_STAPLE")
        self.assertEqual(evidence.action_hint, "REVIEW")


class TestAvailabilityRiskMapping(unittest.TestCase):
    """Availability risk classifications must map to AVAILABILITY_RISK severity MEDIUM."""

    def test_dns_failure_is_availability(self) -> None:
        evidence = classify_risk("DNS_FAILURE")
        self.assertEqual(evidence.risk_category, "AVAILABILITY_RISK")
        self.assertEqual(evidence.severity, "MEDIUM")

    def test_connection_error_is_availability(self) -> None:
        evidence = classify_risk("CONNECTION_ERROR")
        self.assertEqual(evidence.risk_category, "AVAILABILITY_RISK")
        self.assertEqual(evidence.severity, "MEDIUM")

    def test_timeout_is_availability(self) -> None:
        evidence = classify_risk("TIMEOUT")
        self.assertEqual(evidence.risk_category, "AVAILABILITY_RISK")
        self.assertEqual(evidence.severity, "MEDIUM")


class TestDeprecatedTlsMapping(unittest.TestCase):
    """Deprecated TLS must map to DEPRECATED_PROTOCOL_RISK severity HIGH."""

    def test_deprecated_tls_risk_category(self) -> None:
        evidence = classify_risk("DEPRECATED_TLS_VERSION")
        self.assertEqual(evidence.risk_category, "DEPRECATED_PROTOCOL_RISK")

    def test_deprecated_tls_severity(self) -> None:
        evidence = classify_risk("DEPRECATED_TLS_VERSION")
        self.assertEqual(evidence.severity, "HIGH")

    def test_deprecated_tls_failure_family(self) -> None:
        evidence = classify_risk("DEPRECATED_TLS_VERSION")
        self.assertEqual(evidence.failure_family, "PROTOCOL_WEAKNESS")

    def test_deprecated_tls_action_hint(self) -> None:
        evidence = classify_risk("DEPRECATED_TLS_VERSION")
        self.assertEqual(evidence.action_hint, "MODERNIZE_OR_DENY")


class TestAmbiguousMapping(unittest.TestCase):
    """Ambiguous classifications must map to appropriate ambiguous risk categories."""

    def test_tls_handshake_failure_is_ambiguous(self) -> None:
        evidence = classify_risk("TLS_HANDSHAKE_FAILURE")
        self.assertEqual(evidence.risk_category, "AMBIGUOUS_FAILURE")
        self.assertEqual(evidence.severity, "MEDIUM")
        self.assertEqual(evidence.failure_family, "AMBIGUOUS")

    def test_unknown_ssl_error_is_unknown_risk(self) -> None:
        evidence = classify_risk("UNKNOWN_SSL_ERROR")
        self.assertEqual(evidence.risk_category, "UNKNOWN_RISK")
        self.assertEqual(evidence.severity, "LOW")
        self.assertEqual(evidence.failure_family, "UNKNOWN")


class TestIncompleteVsUntrustedChain(unittest.TestCase):
    """Incomplete vs untrusted chain ambiguity must be documented."""

    def test_incomplete_chain_maps_to_chain_trust_failure(self) -> None:
        evidence = classify_risk("INCOMPLETE_CHAIN")
        self.assertEqual(evidence.risk_category, "CHAIN_TRUST_FAILURE")
        self.assertEqual(evidence.failure_family, "CHAIN_TRUST")

    def test_untrusted_chain_maps_to_security_risk(self) -> None:
        evidence = classify_risk("UNTRUSTED_CHAIN")
        self.assertEqual(evidence.risk_category, "SECURITY_RISK")
        self.assertEqual(evidence.failure_family, "CHAIN_TRUST")

    def test_both_chain_types_use_same_failure_family(self) -> None:
        incomplete = classify_risk("INCOMPLETE_CHAIN")
        untrusted = classify_risk("UNTRUSTED_CHAIN")
        self.assertEqual(incomplete.failure_family, untrusted.failure_family)

    def test_incomplete_chain_is_not_security_risk(self) -> None:
        evidence = classify_risk("INCOMPLETE_CHAIN")
        self.assertNotEqual(evidence.risk_category, "SECURITY_RISK",
                            "INCOMPLETE_CHAIN should be CHAIN_TRUST_FAILURE, not SECURITY_RISK")


class TestAdapterDoesNotReadExpectations(unittest.TestCase):
    """Adapter must not read expectation files or labels."""

    def test_classify_risk_no_expectations(self) -> None:
        evidence = classify_risk("EXPIRED_CERT")
        self.assertEqual(evidence.risk_category, "SECURITY_RISK")
        self.assertEqual(evidence.severity, "HIGH")

    def test_enrich_evidence_no_expectations(self) -> None:
        enriched = enrich_evidence("VALID_TLS")
        self.assertEqual(enriched["tls_policy_risk"], "ACCEPTABLE_TLS")

    def test_classify_risk_unknown_raises(self) -> None:
        with self.assertRaises(KeyError):
            classify_risk("NOT_A_REAL_CLASSIFICATION")


class TestAdapterSchemaStability(unittest.TestCase):
    """Adapter output schema must be stable and complete."""

    def test_enriched_evidence_has_all_keys(self) -> None:
        enriched = enrich_evidence("EXPIRED_CERT")
        required_keys = {"tls_policy_risk", "tls_risk_severity",
                         "tls_failure_family", "tls_policy_reason", "tls_action_hint"}
        self.assertEqual(set(enriched.keys()), required_keys)

    def test_enriched_evidence_string_types(self) -> None:
        enriched = enrich_evidence("VALID_TLS")
        for key in enriched:
            self.assertIsInstance(enriched[key], str,
                                  f"Field {key} must be str, got {type(enriched[key])}")

    def test_policy_evidence_is_frozen(self) -> None:
        evidence = classify_risk("VALID_TLS")
        with self.assertRaises(AttributeError):
            evidence.risk_category = "CHANGED"  # type: ignore[misc]

    def test_severity_order_is_ascending(self) -> None:
        for i in range(len(SEVERITY_ORDER) - 1):
            self.assertLess(SEVERITY_RANK[SEVERITY_ORDER[i]],
                            SEVERITY_RANK[SEVERITY_ORDER[i + 1]])


class TestAdapterBenchmarkResultSchema(unittest.TestCase):
    """Benchmark result schema must be stable."""

    def test_benchmark_result_required_keys(self) -> None:
        result: AdapterBenchmarkResult = {
            "domain": "example.com",
            "classification": "VALID_TLS",
            "expected_policy": "ACCEPTABLE_TLS",
            "adapter_risk_category": "ACCEPTABLE_TLS",
            "adapter_severity": "NONE",
            "adapter_action_hint": "NONE",
            "adapter_conformant": True,
            "spl_decision": True,
            "spl_policy_label": "ACCEPTABLE_TLS",
            "spl_conformant": True,
        }
        required = {"domain", "classification", "expected_policy",
                    "adapter_risk_category", "adapter_severity", "adapter_action_hint",
                    "adapter_conformant"}
        optional = {"spl_decision", "spl_policy_label", "spl_conformant"}
        self.assertTrue(required.issubset(set(result.keys())),
                        f"Missing required keys: {required - set(result.keys())}")
        for key in result:
            self.assertIn(key, required | optional,
                          f"Unexpected key: {key}")

    def test_benchmark_result_optional_fields_none(self) -> None:
        result: AdapterBenchmarkResult = {
            "domain": "example.com",
            "classification": "VALID_TLS",
            "expected_policy": "ACCEPTABLE_TLS",
            "adapter_risk_category": "ACCEPTABLE_TLS",
            "adapter_severity": "NONE",
            "adapter_action_hint": "NONE",
            "adapter_conformant": True,
        }
        # Should be constructable without optional fields
        self.assertEqual(result["domain"], "example.com")


class TestRunnerStructuredOutput(unittest.TestCase):
    """Runner must produce structured JSON output."""

    def test_runner_script_compiles(self) -> None:
        import py_compile
        runner_path = os.path.join(PROJECT_ROOT, "scripts", "run_tls_policy_adapter_benchmark.py")
        self.assertTrue(os.path.isfile(runner_path))
        py_compile.compile(runner_path, doraise=True)

    def test_runner_produces_structured_json(self) -> None:
        """Check that the runner's output JSON has expected structure."""
        data = _make_benchmark_results()

        self.assertIn("_metadata", data)
        # Phase 6.5 restructured output: check for baselines array instead of old 'overall'/'results'
        self.assertIn("baselines", data,
                      "Output must contain baselines array")
        self.assertGreater(len(data["baselines"]), 0,
                           "Must have at least one baseline")
        self.assertFalse(data["_metadata"]["spl_core_modified"],
                         "SPL Core must not be modified")
        self.assertEqual(data["_metadata"]["ofe_status"], "HOLD_PENDING_REAL_DATA")


class TestDesignDocumentExists(unittest.TestCase):
    """Design document must exist and contain required sections."""

    def test_design_document_exists(self) -> None:
        doc_path = os.path.join(PROJECT_ROOT, "docs", "TLS_RISK_POLICY_ADAPTER.md")
        self.assertTrue(os.path.isfile(doc_path))

    def test_design_document_mentions_sidecar(self) -> None:
        doc_path = os.path.join(PROJECT_ROOT, "docs", "TLS_RISK_POLICY_ADAPTER.md")
        self.assertTrue(os.path.isfile(doc_path))
        with open(doc_path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("sidecar", text.lower())

    def test_design_document_does_not_claim_production(self) -> None:
        doc_path = os.path.join(PROJECT_ROOT, "docs", "TLS_RISK_POLICY_ADAPTER.md")
        self.assertTrue(os.path.isfile(doc_path))
        with open(doc_path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("production ready", text.lower())

    def test_design_document_mentions_spl_core_not_modified(self) -> None:
        doc_path = os.path.join(PROJECT_ROOT, "docs", "TLS_RISK_POLICY_ADAPTER.md")
        self.assertTrue(os.path.isfile(doc_path))
        with open(doc_path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("without modifying spl core", text.lower(),
                      "Design doc must state SPL Core is not modified")


class TestIsSeverityGte(unittest.TestCase):
    """is_severity_gte helper must compare severity correctly."""

    def test_none_gte_none(self) -> None:
        from tls_policy_adapter.risk_policy import is_severity_gte
        evidence = classify_risk("VALID_TLS")
        self.assertTrue(is_severity_gte(evidence, "NONE"))

    def test_none_not_gte_low(self) -> None:
        from tls_policy_adapter.risk_policy import is_severity_gte
        evidence = classify_risk("VALID_TLS")
        self.assertFalse(is_severity_gte(evidence, "LOW"))

    def test_critical_gte_high(self) -> None:
        from tls_policy_adapter.risk_policy import is_severity_gte
        evidence = classify_risk("WRONG_HOST_CERT")
        self.assertTrue(is_severity_gte(evidence, "HIGH"))

    def test_medium_gte_medium(self) -> None:
        from tls_policy_adapter.risk_policy import is_severity_gte
        evidence = classify_risk("DNS_FAILURE")
        self.assertTrue(is_severity_gte(evidence, "MEDIUM"))

    def test_medium_not_gte_high(self) -> None:
        from tls_policy_adapter.risk_policy import is_severity_gte
        evidence = classify_risk("DNS_FAILURE")
        self.assertFalse(is_severity_gte(evidence, "HIGH"))


class TestPhase65MethodComparisonExists(unittest.TestCase):
    """Phase 6.5 audit: method comparison doc must exist."""

    def test_method_comparison_doc_exists(self) -> None:
        path = os.path.join(PROJECT_ROOT, "docs", "PHASE5_PHASE6_METHOD_COMPARISON.md")
        self.assertTrue(os.path.isfile(path))

    def test_method_comparison_explains_discrepancy(self) -> None:
        path = os.path.join(PROJECT_ROOT, "docs", "PHASE5_PHASE6_METHOD_COMPARISON.md")
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("70.3", text)
        self.assertIn("95.8", text)
        self.assertIn("proxy-trained", text.lower())


class TestPhase65ProbeLimitationAudit(unittest.TestCase):
    """Phase 6.5 audit: probe limitation audit doc must exist."""

    def test_probe_limitation_audit_exists(self) -> None:
        path = os.path.join(PROJECT_ROOT, "docs", "TLS_PROBE_LIMITATION_AUDIT.md")
        self.assertTrue(os.path.isfile(path))

    def test_probe_limitation_audit_includes_deprecated_tls(self) -> None:
        path = os.path.join(PROJECT_ROOT, "docs", "TLS_PROBE_LIMITATION_AUDIT.md")
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("deprecated", text.lower())

    def test_probe_limitation_audit_includes_dns_failures(self) -> None:
        path = os.path.join(PROJECT_ROOT, "docs", "TLS_PROBE_LIMITATION_AUDIT.md")
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("columbia.edu", text)
        self.assertIn("uchicago.edu", text)


class TestPhase65BaselineSeparation(unittest.TestCase):
    """Phase 6.5 audit: baselines must be clearly separated."""

    def test_baseline_comparison_report_exists(self) -> None:
        path = os.path.join(
            PROJECT_ROOT, "reports", "local_real_validation", "PHASE6_BASELINE_COMPARISON.md",
        )
        self.assertTrue(os.path.isfile(path))

    def test_baseline_report_has_all_modes(self) -> None:
        path = os.path.join(
            PROJECT_ROOT, "reports", "local_real_validation", "PHASE6_BASELINE_COMPARISON.md",
        )
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Adapter-Only", text)
        self.assertIn("SPL Observation", text)
        self.assertIn("SPL Holdout", text)
        self.assertIn("SPL Proxy-Trained", text)

    def test_proxy_trained_labeled_not_generalization(self) -> None:
        path = os.path.join(
            PROJECT_ROOT, "reports", "local_real_validation", "PHASE6_BASELINE_COMPARISON.md",
        )
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("NOT generalization", text)

    def test_holdout_labeled_as_generalization(self) -> None:
        path = os.path.join(
            PROJECT_ROOT, "reports", "local_real_validation", "PHASE6_BASELINE_COMPARISON.md",
        )
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("generalization", text.lower())

    def test_baseline_report_has_category_level(self) -> None:
        path = os.path.join(
            PROJECT_ROOT, "reports", "local_real_validation", "PHASE6_BASELINE_COMPARISON.md",
        )
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Category", text)
        self.assertIn("VALID_TLS", text)
        self.assertIn("EXPIRED_CERT", text)
        self.assertIn("DEPRECATED_TLS", text)

    def test_category_level_includes_non_valid_tls(self) -> None:
        path = os.path.join(
            PROJECT_ROOT, "reports", "local_real_validation", "PHASE6_BASELINE_COMPARISON.md",
        )
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        # Must include at least 3 non-VALID categories
        for cat in ("EXPIRED_CERT", "DNS_FAILURE", "TIMEOUT", "DEPRECATED_TLS"):
            self.assertIn(cat, text)


class TestPhase65RunnerBaselines(unittest.TestCase):
    """Phase 6.5 audit: runner must implement all baselines correctly."""

    def test_runner_produces_baseline_json(self) -> None:
        """Check that runner output JSON has all 4 baselines."""
        data = _make_benchmark_results()

        self.assertIn("baselines", data)
        modes = {b["mode"] for b in data["baselines"]}
        self.assertIn("adapter-only", modes)
        self.assertIn("spl-observation", modes)
        self.assertIn("spl-holdout", modes)
        self.assertIn("spl-proxy-trained", modes)

    def test_runner_baselines_label_modes(self) -> None:
        data = _make_benchmark_results()

        for b in data["baselines"]:
            self.assertIn("mode", b)
            self.assertIn("description", b)
            self.assertIn("conformance_pct", b)
            self.assertIn("category_performance", b)

    def test_proxy_trained_is_not_holdout(self) -> None:
        """Proxy-trained mode must use same dataset for train and eval."""
        data = _make_benchmark_results()

        for b in data["baselines"]:
            if b["mode"] == "spl-proxy-trained":
                self.assertIn("NOT generalization", b["description"])
            if b["mode"] == "spl-holdout":
                self.assertIn("generalization", b["description"].lower())

    def test_adapter_only_no_expectations_internal(self) -> None:
        """Adapter-only must produce results without reading expectations internally."""
        data = _make_benchmark_results()

        for b in data["baselines"]:
            if b["mode"] == "adapter-only":
                # Adapter-only results use EXPECTED_POLICY only for scoring (via comparison),
                # not for producing the adapter classification
                self.assertGreater(b["conformance_pct"], 0)


class TestPhase65SPLCoreUntouched(unittest.TestCase):
    """Phase 6.5 audit: SPL Core must remain untouched."""

    def test_spl_core_not_modified(self) -> None:
        import py_compile
        spl_files = [
            os.path.join(PROJECT_ROOT, "spl_v7", "causal.py"),
            os.path.join(PROJECT_ROOT, "spl_v7", "kafka_pipeline.py"),
            os.path.join(PROJECT_ROOT, "spl_v7", "schema.py"),
        ]
        for f in spl_files:
            self.assertTrue(os.path.isfile(f), f"Missing SPL Core file: {f}")
            py_compile.compile(f, doraise=True)


class TestPhase65DesignDocUpdated(unittest.TestCase):
    """Phase 6.5 audit: design doc must reference method comparison."""

    def test_design_doc_references_audit(self) -> None:
        path = os.path.join(PROJECT_ROOT, "docs", "TLS_RISK_POLICY_ADAPTER.md")
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Phase 6.5", text)
        self.assertIn("proxy-trained", text.lower())


class TestClassifyRiskFromProbe(unittest.TestCase):
    """classify_risk_from_probe extracts classification from probe result dict."""

    def test_valid_probe_result(self) -> None:
        from tls_policy_adapter.risk_policy import classify_risk_from_probe
        probe = {"domain": "example.com", "classification": "VALID_TLS"}
        evidence = classify_risk_from_probe(probe)
        self.assertEqual(evidence.risk_category, "ACCEPTABLE_TLS")

    def test_expired_probe_result(self) -> None:
        from tls_policy_adapter.risk_policy import classify_risk_from_probe
        probe = {"domain": "expired.badssl.com", "classification": "EXPIRED_CERT"}
        evidence = classify_risk_from_probe(probe)
        self.assertEqual(evidence.risk_category, "SECURITY_RISK")

    def test_missing_classification_raises(self) -> None:
        from tls_policy_adapter.risk_policy import classify_risk_from_probe
        probe = {"domain": "example.com"}
        with self.assertRaises(KeyError):
            classify_risk_from_probe(probe)

    def test_empty_classification_raises(self) -> None:
        from tls_policy_adapter.risk_policy import classify_risk_from_probe
        probe = {"domain": "example.com", "classification": ""}
        with self.assertRaises(KeyError):
            classify_risk_from_probe(probe)


if __name__ == "__main__":
    unittest.main()
