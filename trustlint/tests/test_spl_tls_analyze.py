"""Tests for TrustLint CLI.

All tests use mocks - no live network calls.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from typing import Any, Dict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.spl_tls_analyze import (
    parse_args,
    resolve_targets,
    compute_exit_code,
    compute_summary,
    format_structured_text,
    format_json_output,
    format_markdown_output,
    format_batch_summary,
    analyze_domain,
    _get_recommended_action,
    _build_evidence_artifact,
    _RECOMMENDED_ACTIONS,
    DEPRECATED_TLS_VERSIONS,
)


def _make_mock_probe(
    domain: str = "example.com",
    classification: str = "VALID_TLS",
    tls_version: str = "TLSv1.3",
    expiry_days: int = 89,
    resolved_ip: str = "1.2.3.4",
    cert_is_expired: bool = False,
    chain_complete: bool = True,
    dns_error: str | None = None,
    ocsp_status: str | None = None,
    ocsp_error: str | None = None,
    ocsp_performed: bool = False,
    deprecated_tls_detected: bool = False,
    deprecated_tls_check: str = "supported",
) -> Dict[str, Any]:
    tls: Dict[str, Any] | None
    if classification in ("DNS_FAILURE",):
        tls = None
    else:
        tls = {
            "tls_version": tls_version,
            "cert_expiry_days": expiry_days,
            "cert_is_expired": cert_is_expired,
            "cert_chain_complete": chain_complete,
            "handshake_time_ms": 45.2,
            "ocsp_performed": ocsp_performed,
            "ocps_stapled": False,
            "ocsp_status": ocsp_status,
            "ocsp_error": ocsp_error,
            "ocsp_responder_url": None,
            "deprecated_tls_detected": deprecated_tls_detected,
            "deprecated_tls_check": deprecated_tls_check,
        }

    effective_classification = classification
    if deprecated_tls_detected:
        effective_classification = "DEPRECATED_TLS_VERSION"
    elif ocsp_status == "revoked":
        effective_classification = "REVOKED_CERT"
    elif ocsp_status == "unreachable" and classification == "VALID_TLS":
        effective_classification = "OCSP_UNREACHABLE"

    return {
        "domain": domain,
        "probe_timestamp": "2026-06-01T12:00:00Z",
        "resolved_ip": resolved_ip if classification != "DNS_FAILURE" else None,
        "dns_error": dns_error,
        "tls": tls,
        "overall_status": effective_classification.lower(),
        "classification": effective_classification,
    }


class TestResolveTargets(unittest.TestCase):
    def test_single_domain(self) -> None:
        self.assertEqual(resolve_targets("example.com"), ["example.com"])

    def test_file_input(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("example.com\n")
            f.write("test.org\n")
            f.write("# comment\n")
            f.write("  spaced.com  \n")
            tmp = f.name
        try:
            domains = resolve_targets(tmp)
            self.assertEqual(domains, ["example.com", "test.org", "spaced.com"])
        finally:
            os.unlink(tmp)

    def test_nonexistent_path_treated_as_domain(self) -> None:
        """If the path is not a file, resolve_targets treats it as a domain."""
        self.assertEqual(resolve_targets("nonexistent_file_xyz.txt"), ["nonexistent_file_xyz.txt"])


class TestExitCodes(unittest.TestCase):
    def test_exit_code_0_all_allow(self) -> None:
        results = [
            {"final": {"decision": "ALLOW"}},
            {"final": {"decision": "ALLOW"}},
        ]
        self.assertEqual(compute_exit_code(results), 0)

    def test_exit_code_1_review_no_deny(self) -> None:
        results = [
            {"final": {"decision": "ALLOW"}},
            {"final": {"decision": "REVIEW"}},
        ]
        self.assertEqual(compute_exit_code(results), 1)

    def test_exit_code_2_deny(self) -> None:
        results = [
            {"final": {"decision": "ALLOW"}},
            {"final": {"decision": "DENY"}},
        ]
        self.assertEqual(compute_exit_code(results), 2)

    def test_exit_code_2_deny_overrides_review(self) -> None:
        results = [
            {"final": {"decision": "REVIEW"}},
            {"final": {"decision": "DENY"}},
        ]
        self.assertEqual(compute_exit_code(results), 2)


class TestComputeSummary(unittest.TestCase):
    def test_summary_counts(self) -> None:
        results = [
            {"final": {"decision": "ALLOW", "risk": "NONE"}, "tls_probe": {"is_probe_limited": False, "classification": "VALID_TLS"}},
            {"final": {"decision": "REVIEW", "risk": "HIGH"}, "tls_probe": {"is_probe_limited": True, "classification": "EXPIRED_CERT"}},
            {"final": {"decision": "DENY", "risk": "CRITICAL"}, "tls_probe": {"is_probe_limited": False, "classification": "WRONG_HOST_CERT"}},
        ]
        s = compute_summary(results)
        self.assertEqual(s["total_domains"], 3)
        self.assertEqual(s["allow"], 1)
        self.assertEqual(s["review"], 1)
        self.assertEqual(s["deny"], 1)
        self.assertEqual(s["probe_limited"], 1)
        self.assertEqual(s["highest_risk"], "CRITICAL")

    def test_highest_risk_none(self) -> None:
        results = [
            {"final": {"decision": "ALLOW", "risk": "NONE"}, "tls_probe": {"is_probe_limited": False, "classification": "VALID_TLS"}},
        ]
        s = compute_summary(results)
        self.assertEqual(s["highest_risk"], "NONE")


class TestRecommendedActions(unittest.TestCase):
    def test_all_classifications_have_actions(self) -> None:
        from tls_policy_adapter.schema import RISK_MAP
        for cls in RISK_MAP:
            self.assertIn(cls, _RECOMMENDED_ACTIONS,
                          f"Missing recommended action for {cls}")

    def test_valid_tls_allow(self) -> None:
        self.assertEqual(
            _get_recommended_action("VALID_TLS", "ALLOW"),
            "No action required.",
        )

    def test_expired_cert(self) -> None:
        action = _get_recommended_action("EXPIRED_CERT", "REVIEW")
        self.assertIn("Renew", action)

    def test_wrong_host_cert(self) -> None:
        action = _get_recommended_action("WRONG_HOST_CERT", "DENY")
        self.assertIn("hostname", action.lower())

    def test_dns_failure(self) -> None:
        action = _get_recommended_action("DNS_FAILURE", "REVIEW")
        self.assertIn("DNS", action)

    def test_deprecated_tls(self) -> None:
        action = _get_recommended_action("DEPRECATED_TLS_VERSION", "REVIEW")
        self.assertIn("TLS 1.0", action)

    def test_unknown_ssl_error(self) -> None:
        action = _get_recommended_action("UNKNOWN_SSL_ERROR", "REVIEW")
        self.assertIn("Investigate", action)


class TestAnalyzeDomainMocked(unittest.TestCase):
    @patch("trustlint.analyzer.probe_domain")
    def test_valid_tls_allow_via_fallback_balanced(self, mock_probe: MagicMock) -> None:
        """With balanced profile, clean VALID_TLS without SPL produces ALLOW via fallback."""
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")
        r = analyze_domain("example.com", profile="balanced", timeout=10.0)
        self.assertEqual(r["domain"], "example.com")
        self.assertEqual(r["profile"], "balanced")
        self.assertEqual(r["tls_probe"]["classification"], "VALID_TLS")
        self.assertEqual(r["tls_probe"]["tls_version"], "TLSv1.3")
        self.assertEqual(r["policy_adapter"]["risk_category"], "ACCEPTABLE_TLS")
        self.assertEqual(r["spl"]["decision"], None)
        self.assertEqual(r["spl"]["confidence_source"], "FALLBACK")
        self.assertEqual(r["final"]["decision"], "ALLOW")
        self.assertEqual(r["final"]["risk"], "NONE")
        self.assertTrue(r["final"]["fallback_used"])
        self.assertEqual(r["final"]["source"], "ADAPTER_FALLBACK")
        self.assertEqual(r["final"]["recommended_action"], "No action required.")
        self.assertEqual(r["ofe_observed"], False)

    @patch("trustlint.analyzer.probe_domain")
    def test_valid_tls_review_conservative_without_spl(self, mock_probe: MagicMock) -> None:
        """Without SPL confidence, conservative profile keeps VALID_TLS as REVIEW."""
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")
        r = analyze_domain("example.com", profile="conservative", timeout=10.0)
        self.assertEqual(r["domain"], "example.com")
        self.assertEqual(r["profile"], "conservative")
        self.assertEqual(r["final"]["decision"], "REVIEW")
        self.assertEqual(r["final"]["risk"], "LOW")
        self.assertFalse(r["final"]["fallback_used"])

    @patch("trustlint.analyzer.probe_domain")
    def test_expired_cert_review(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe(
            "expired.example.com", "EXPIRED_CERT",
            tls_version="TLSv1.2", expiry_days=-1, cert_is_expired=True,
        )
        r = analyze_domain("expired.example.com", profile="balanced")
        self.assertEqual(r["tls_probe"]["classification"], "EXPIRED_CERT")
        self.assertEqual(r["policy_adapter"]["risk_category"], "SECURITY_RISK")
        self.assertEqual(r["policy_adapter"]["severity"], "HIGH")
        self.assertEqual(r["final"]["decision"], "REVIEW")
        self.assertIn("Renew", r["final"]["recommended_action"])

    @patch("trustlint.analyzer.probe_domain")
    def test_wrong_host_cert_deny(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe(
            "wronghost.example.com", "WRONG_HOST_CERT",
            tls_version="TLSv1.2", expiry_days=200,
        )
        r = analyze_domain("wronghost.example.com")
        self.assertEqual(r["tls_probe"]["classification"], "WRONG_HOST_CERT")
        self.assertEqual(r["policy_adapter"]["risk_category"], "SECURITY_RISK")
        self.assertEqual(r["policy_adapter"]["severity"], "CRITICAL")
        self.assertEqual(r["final"]["decision"], "DENY")
        self.assertIn("hostname", r["final"]["recommended_action"].lower())

    @patch("trustlint.analyzer.probe_domain")
    def test_dns_failure_review(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe(
            "dnsfail.example.com", "DNS_FAILURE",
            dns_error="Name or service not known",
        )
        r = analyze_domain("dnsfail.example.com")
        self.assertEqual(r["tls_probe"]["classification"], "DNS_FAILURE")
        self.assertTrue(r["tls_probe"]["is_probe_limited"])
        self.assertIn("DNS", r["tls_probe"]["warnings"][0])
        self.assertEqual(r["final"]["decision"], "REVIEW")

    @patch("trustlint.analyzer.probe_domain")
    def test_strict_profile_denies_high_security(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe(
            "strict.example.com", "EXPIRED_CERT",
            tls_version="TLSv1.2", expiry_days=-1,
        )
        r = analyze_domain("strict.example.com", profile="strict")
        self.assertEqual(r["final"]["decision"], "DENY")

    @patch("trustlint.analyzer.probe_domain")
    def test_conservative_profile_reviews_high_security(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe(
            "conservative.example.com", "EXPIRED_CERT",
            tls_version="TLSv1.2", expiry_days=-1,
        )
        r = analyze_domain("conservative.example.com", profile="conservative")
        self.assertEqual(r["final"]["decision"], "REVIEW")

    @patch("trustlint.analyzer.probe_domain")
    def test_deprecated_tls_detected(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe(
            "old.example.com", "VALID_TLS", tls_version="TLSv1",
            expiry_days=30,
        )
        r = analyze_domain("old.example.com")
        self.assertEqual(r["tls_probe"]["classification"], "DEPRECATED_TLS_VERSION")
        self.assertEqual(r["policy_adapter"]["risk_category"], "DEPRECATED_PROTOCOL_RISK")
        self.assertIn("Deprecated TLS", " ".join(r["tls_probe"]["warnings"]))

    @patch("trustlint.analyzer.probe_domain")
    def test_ofe_never_affects_decision(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")
        r = analyze_domain("example.com")
        self.assertEqual(r["ofe_observed"], False)
        self.assertIn(r["final"]["decision"], ("REVIEW", "ALLOW"))

    @patch("trustlint.analyzer.probe_domain")
    def test_output_schema_stability(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")
        r = analyze_domain("example.com")
        required_top = {"domain", "profile", "probe_timestamp", "tls_probe",
                        "policy_adapter", "spl", "final", "ofe_observed"}
        self.assertTrue(required_top.issubset(r.keys()), f"Missing keys: {required_top - r.keys()}")

        required_tls = {"classification", "tls_version", "expiry_days", "warnings",
                         "is_probe_limited", "ocsp_performed", "ocsp_stapled",
                         "ocsp_status", "ocsp_error", "ocsp_responder_url",
                         "deprecated_tls_check", "deprecated_tls_detected"}
        self.assertTrue(required_tls.issubset(r["tls_probe"].keys()))

        required_pa = {"risk_category", "severity", "failure_family", "reason", "action_hint"}
        self.assertTrue(required_pa.issubset(r["policy_adapter"].keys()))

        required_spl = {"decision", "confidence", "confidence_source", "weakness_flags"}
        self.assertTrue(required_spl.issubset(r["spl"].keys()))

        required_final = {"decision", "risk", "source", "fallback_used",
                          "primary_reason", "supporting_reasons",
                          "recommended_action", "limitations"}
        self.assertTrue(required_final.issubset(r["final"].keys()))

    @patch("trustlint.analyzer.probe_domain")
    def test_fallback_used_in_json_output(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")
        r = analyze_domain("example.com", profile="balanced")
        self.assertTrue(r["final"]["fallback_used"])
        self.assertEqual(r["final"]["source"], "ADAPTER_FALLBACK")

    @patch("trustlint.analyzer.probe_domain")
    def test_confidence_source_in_spl_output(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")
        r = analyze_domain("example.com", profile="balanced")
        self.assertEqual(r["spl"]["confidence_source"], "FALLBACK")

    @patch("trustlint.analyzer.probe_domain")
    def test_fallback_used_in_console_output(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")
        r = analyze_domain("example.com", profile="balanced")
        text = format_structured_text(r)
        self.assertIn("Fallback Used", text)
        self.assertIn("ADAPTER_FALLBACK", text)

    @patch("trustlint.analyzer.probe_domain")
    def test_fallback_in_markdown_output(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")
        r = analyze_domain("example.com", profile="balanced")
        md = format_markdown_output([r], "balanced")
        self.assertIn("Fallback ALLOW (adapter policy)", md)
        self.assertIn("allowed via fallback", md.lower())

    @patch("trustlint.analyzer.probe_domain")
    def test_exit_code_0_for_all_allow_fallback(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("good.com", "VALID_TLS")
        r1 = analyze_domain("good.com", profile="balanced")
        r2 = analyze_domain("better.com", profile="balanced")
        exit_code = compute_exit_code([r1, r2])
        self.assertEqual(exit_code, 0)

    @patch("trustlint.analyzer.probe_domain")
    def test_exit_code_2_for_deny_with_fallback_elsewhere(self, mock_probe: MagicMock) -> None:
        def side_effect(domain: str, **kwargs: Any) -> Dict[str, Any]:
            if "bad" in domain:
                return _make_mock_probe(domain, "WRONG_HOST_CERT", tls_version="TLSv1.2")
            return _make_mock_probe(domain, "VALID_TLS")
        mock_probe.side_effect = side_effect
        r1 = analyze_domain("good.com", profile="balanced")
        r2 = analyze_domain("bad.com", profile="balanced")
        exit_code = compute_exit_code([r1, r2])
        self.assertEqual(exit_code, 2)
        self.assertTrue(r1["final"]["fallback_used"])
        self.assertFalse(r2["final"]["fallback_used"])

    @patch("trustlint.analyzer.probe_domain")
    def test_fallback_count_in_batch_summary(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("good.com", "VALID_TLS")
        r1 = analyze_domain("good.com", profile="balanced")
        r2 = analyze_domain("better.com", profile="balanced")
        summary = compute_summary([r1, r2])
        self.assertEqual(summary["fallback"], 2)
        self.assertEqual(summary["allow"], 2)

    @patch("trustlint.analyzer.probe_domain")
    def test_no_fallback_for_dns_failure(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe(
            "dnsfail.example.com", "DNS_FAILURE",
            dns_error="Name or service not known",
        )
        r = analyze_domain("dnsfail.example.com", profile="balanced")
        self.assertFalse(r["final"]["fallback_used"])
        self.assertEqual(r["final"]["decision"], "REVIEW")


class TestStructuredTextOutput(unittest.TestCase):
    def test_sections_exist(self) -> None:
        result = {
            "domain": "test.com",
            "profile": "balanced",
            "tls_probe": {"classification": "VALID_TLS", "tls_version": "TLSv1.3",
                          "expiry_days": 89, "resolved_ip": "1.2.3.4",
                          "cert_is_expired": False, "chain_complete": True,
                          "handshake_time_ms": 45.2, "warnings": [],
                          "is_probe_limited": False},
            "policy_adapter": {"risk_category": "ACCEPTABLE_TLS", "severity": "NONE",
                               "failure_family": "NONE", "reason": "OK",
                               "action_hint": "NONE"},
            "spl": {"decision": None, "confidence": None, "weakness_flags": []},
            "final": {"decision": "ALLOW", "risk": "NONE", "source": "ADAPTER",
                      "primary_reason": "Test reason",
                      "supporting_reasons": ["Profile: balanced"],
                      "recommended_action": "No action required.",
                      "limitations": []},
            "ofe_observed": False,
        }
        text = format_structured_text(result)
        self.assertIn("[TLS Probe]", text)
        self.assertIn("[Policy Adapter]", text)
        self.assertIn("[SPL]", text)
        self.assertIn("[Decision Reasoning]", text)
        self.assertIn("[Recommended Action]", text)

    def test_limitations_section_appears_when_present(self) -> None:
        result = {
            "domain": "bad.com",
            "profile": "balanced",
            "tls_probe": {"classification": "DNS_FAILURE", "tls_version": None,
                          "expiry_days": None, "resolved_ip": None,
                          "cert_is_expired": False, "chain_complete": None,
                          "handshake_time_ms": None,
                          "warnings": ["DNS resolution failed"],
                          "is_probe_limited": True},
            "policy_adapter": {"risk_category": "AVAILABILITY_RISK", "severity": "MEDIUM",
                               "failure_family": "AVAILABILITY", "reason": "DNS failure",
                               "action_hint": "REVIEW"},
            "spl": {"decision": None, "confidence": None, "weakness_flags": []},
            "final": {"decision": "REVIEW", "risk": "MEDIUM", "source": "ADAPTER",
                      "primary_reason": "Availability risk",
                      "supporting_reasons": [],
                      "recommended_action": "Check DNS records",
                      "limitations": ["DNS resolution failed"]},
            "ofe_observed": False,
        }
        text = format_structured_text(result)
        self.assertIn("[Limitations]", text)
        self.assertIn("DNS resolution failed", text)


class TestBatchSummary(unittest.TestCase):
    def test_batch_summary_sections(self) -> None:
        results = [
            {"final": {"decision": "ALLOW", "risk": "NONE", "recommended_action": "No action"},
             "tls_probe": {"is_probe_limited": False, "classification": "VALID_TLS"},
             "domain": "good.com"},
            {"final": {"decision": "REVIEW", "risk": "HIGH", "recommended_action": "Renew cert",
                       "primary_reason": "Expired"},
             "tls_probe": {"is_probe_limited": False, "classification": "EXPIRED_CERT",
                           "warnings": []},
             "domain": "bad.com"},
            {"final": {"decision": "DENY", "risk": "CRITICAL", "recommended_action": "Replace cert",
                       "primary_reason": "Wrong host"},
             "tls_probe": {"is_probe_limited": False, "classification": "WRONG_HOST_CERT",
                           "warnings": []},
             "domain": "wrong.com"},
        ]
        for r in results:
            r["final"] = dict(r["final"])
            r["tls_probe"] = dict(r["tls_probe"])
        summary = format_batch_summary(results)
        self.assertIn("BATCH SUMMARY", summary)
        self.assertIn("Immediate Action", summary)
        self.assertIn("Manual Review", summary)


class TestJsonOutput(unittest.TestCase):
    def test_json_schema(self) -> None:
        results = [
            {"domain": "test.com", "profile": "balanced",
             "tls_probe": {"classification": "VALID_TLS", "tls_version": "TLSv1.3",
                           "expiry_days": 89, "resolved_ip": "1.2.3.4",
                           "cert_is_expired": False, "chain_complete": True,
                           "handshake_time_ms": 45.2, "warnings": [],
                           "is_probe_limited": False},
             "policy_adapter": {"risk_category": "ACCEPTABLE_TLS", "severity": "NONE",
                                "failure_family": "NONE", "reason": "OK",
                                "action_hint": "NONE"},
             "spl": {"decision": None, "confidence": None, "weakness_flags": []},
             "final": {"decision": "ALLOW", "risk": "NONE", "source": "ADAPTER",
                       "primary_reason": "Test", "supporting_reasons": [],
                       "recommended_action": "No action", "limitations": []},
             "ofe_observed": False},
        ]
        json_str = format_json_output(results, "balanced")
        parsed = json.loads(json_str)
        self.assertIn("metadata", parsed)
        self.assertEqual(parsed["metadata"]["tool"], "trustlint")
        self.assertEqual(parsed["metadata"]["production_ready"], False)
        self.assertEqual(parsed["metadata"]["scope"], "local-only")
        self.assertIn("summary", parsed)
        self.assertIn("results", parsed)
        self.assertEqual(len(parsed["results"]), 1)


class TestMarkdownOutput(unittest.TestCase):
    def test_markdown_sections(self) -> None:
        results = [
            {"domain": "test.com", "profile": "balanced",
             "tls_probe": {"classification": "VALID_TLS", "tls_version": "TLSv1.3",
                           "expiry_days": 89, "resolved_ip": "1.2.3.4",
                           "cert_is_expired": False, "chain_complete": True,
                           "handshake_time_ms": 45.2, "warnings": [],
                           "is_probe_limited": False},
             "policy_adapter": {"risk_category": "ACCEPTABLE_TLS", "severity": "NONE",
                                "failure_family": "NONE", "reason": "OK",
                                "action_hint": "NONE"},
             "spl": {"decision": None, "confidence": None, "weakness_flags": []},
             "final": {"decision": "ALLOW", "risk": "NONE", "source": "ADAPTER",
                       "primary_reason": "Test", "supporting_reasons": [],
                       "recommended_action": "No action", "limitations": []},
             "ofe_observed": False},
        ]
        md = format_markdown_output(results, "balanced")
        self.assertIn("Executive Summary", md)
        self.assertIn("Full Per-Domain Results", md)
        self.assertIn("Not production ready", md)
        self.assertIn("TrustLint", md)


class TestArgParse(unittest.TestCase):
    def test_defaults(self) -> None:
        args = parse_args(["example.com"])
        self.assertEqual(args.target, "example.com")
        self.assertEqual(args.profile, "balanced")
        self.assertEqual(args.timeout, 10.0)
        self.assertFalse(args.json_out)
        self.assertFalse(args.markdown_out)
        self.assertFalse(args.quiet)
        self.assertFalse(args.verbose)

    def test_profile_flag(self) -> None:
        args = parse_args(["example.com", "--profile", "strict"])
        self.assertEqual(args.profile, "strict")

    def test_json_out(self) -> None:
        args = parse_args(["domains.txt", "--json-out", "out.json"])
        self.assertEqual(args.json_out, "out.json")

    def test_markdown_out(self) -> None:
        args = parse_args(["domains.txt", "--markdown-out", "out.md"])
        self.assertEqual(args.markdown_out, "out.md")

    def test_timeout(self) -> None:
        args = parse_args(["example.com", "--timeout", "15.5"])
        self.assertEqual(args.timeout, 15.5)

    def test_quiet_flag(self) -> None:
        args = parse_args(["example.com", "--quiet"])
        self.assertTrue(args.quiet)

    def test_verbose_flag(self) -> None:
        args = parse_args(["example.com", "--verbose"])
        self.assertTrue(args.verbose)

    def test_invalid_profile(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args(["example.com", "--profile", "invalid"])

    def test_spl_flag(self) -> None:
        args = parse_args(["example.com", "--spl-unsafe"])
        self.assertTrue(args.spl_unsafe)

    def test_spl_flag_default_false(self) -> None:
        args = parse_args(["example.com"])
        self.assertFalse(args.spl_unsafe)


class TestOCSPClassification(unittest.TestCase):
    @patch("trustlint.analyzer.probe_domain")
    def test_revoked_cert_on_ocsp_revoked(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe(
            "revoked.example.com", "VALID_TLS", ocsp_status="revoked", ocsp_performed=True,
        )
        r = analyze_domain("revoked.example.com")
        self.assertEqual(r["tls_probe"]["classification"], "REVOKED_CERT")
        self.assertEqual(r["tls_probe"]["ocsp_status"], "revoked")
        self.assertEqual(r["policy_adapter"]["risk_category"], "SECURITY_RISK")
        self.assertEqual(r["policy_adapter"]["severity"], "CRITICAL")
        self.assertEqual(r["final"]["decision"], "DENY")
        self.assertIn("revoked", r["tls_probe"]["warnings"][0].lower())

    @patch("trustlint.analyzer.probe_domain")
    def test_ocsp_unreachable_on_timeout(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe(
            "unreachable.example.com", "VALID_TLS",
            ocsp_status="unreachable", ocsp_error="OCSP responder unreachable or timed out (>2s)",
        )
        r = analyze_domain("unreachable.example.com")
        self.assertEqual(r["tls_probe"]["classification"], "OCSP_UNREACHABLE")
        self.assertEqual(r["tls_probe"]["ocsp_status"], "unreachable")
        self.assertEqual(r["policy_adapter"]["risk_category"], "AVAILABILITY_RISK")
        self.assertEqual(r["policy_adapter"]["severity"], "MEDIUM")
        self.assertEqual(r["final"]["decision"], "REVIEW")
        self.assertIn("unreachable", r["tls_probe"]["warnings"][0].lower())

    @patch("trustlint.analyzer.probe_domain")
    def test_ocsp_unreachable_only_overrides_valid_tls(self, mock_probe: MagicMock) -> None:
        """OCSP_UNREACHABLE should NOT override EXPIRED_CERT or other errors."""
        mock_probe.return_value = _make_mock_probe(
            "expired.example.com", "EXPIRED_CERT",
            tls_version="TLSv1.2", expiry_days=-1, cert_is_expired=True,
            ocsp_status="unreachable", ocsp_error="timeout",
        )
        r = analyze_domain("expired.example.com")
        self.assertEqual(r["tls_probe"]["classification"], "EXPIRED_CERT")
        self.assertNotEqual(r["tls_probe"]["classification"], "OCSP_UNREACHABLE")

    @patch("trustlint.analyzer.probe_domain")
    def test_valid_tls_with_ocsp_good(self, mock_probe: MagicMock) -> None:
        """When OCSP succeeds and says good, keep VALID_TLS."""
        mock_probe.return_value = _make_mock_probe(
            "good.example.com", "VALID_TLS", ocsp_status="good", ocsp_performed=True,
        )
        r = analyze_domain("good.example.com")
        self.assertEqual(r["tls_probe"]["classification"], "VALID_TLS")
        self.assertTrue(r["tls_probe"]["ocsp_performed"])

    @patch("trustlint.analyzer.probe_domain")
    def test_ocsp_fields_in_output(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")
        r = analyze_domain("example.com")
        self.assertIn("ocsp_performed", r["tls_probe"])
        self.assertIn("ocsp_status", r["tls_probe"])

    @patch("trustlint.analyzer.probe_domain")
    def test_ocsp_fields_in_structured_text(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe(
            "example.com", "VALID_TLS", ocsp_status="good", ocsp_performed=True,
        )
        r = analyze_domain("example.com")
        text = format_structured_text(r)
        self.assertIn("OCSP Status", text)

    @patch("trustlint.analyzer.probe_domain")
    def test_revoked_cert_in_json_output(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe(
            "revoked.example.com", "VALID_TLS", ocsp_status="revoked", ocsp_performed=True,
        )
        r = analyze_domain("revoked.example.com")
        json_str = format_json_output([r], "balanced")
        parsed = json.loads(json_str)
        self.assertEqual(parsed["results"][0]["tls_probe"]["classification"], "REVOKED_CERT")


class TestDeprecatedTLSDetection(unittest.TestCase):
    @patch("trustlint.analyzer.probe_domain")
    def test_deprecated_tls_detected(self, mock_probe: MagicMock) -> None:
        """When secondary TLS 1.1 probe succeeds, classify as DEPRECATED_TLS_VERSION."""
        mock_probe.return_value = _make_mock_probe(
            "old.example.com", "VALID_TLS", tls_version="TLSv1.3",
            deprecated_tls_detected=True, deprecated_tls_check="supported",
        )
        r = analyze_domain("old.example.com")
        self.assertEqual(r["tls_probe"]["classification"], "DEPRECATED_TLS_VERSION")
        self.assertTrue(r["tls_probe"]["deprecated_tls_detected"])
        self.assertEqual(r["tls_probe"]["deprecated_tls_check"], "supported")
        self.assertEqual(r["policy_adapter"]["risk_category"], "DEPRECATED_PROTOCOL_RISK")
        self.assertEqual(r["final"]["decision"], "REVIEW")
        self.assertIn("Deprecated TLS version detected", " ".join(r["tls_probe"]["warnings"]))

    @patch("trustlint.analyzer.probe_domain")
    def test_deprecated_tls_not_detected(self, mock_probe: MagicMock) -> None:
        """Modern server that only supports TLS 1.2+ stays VALID_TLS."""
        mock_probe.return_value = _make_mock_probe(
            "modern.example.com", "VALID_TLS", tls_version="TLSv1.3",
            deprecated_tls_detected=False, deprecated_tls_check="supported",
        )
        r = analyze_domain("modern.example.com")
        self.assertEqual(r["tls_probe"]["classification"], "VALID_TLS")
        self.assertFalse(r["tls_probe"]["deprecated_tls_detected"])
        self.assertEqual(r["tls_probe"]["deprecated_tls_check"], "supported")

    @patch("trustlint.analyzer.probe_domain")
    def test_deprecated_tls_unavailable_on_platform(self, mock_probe: MagicMock) -> None:
        """When OpenSSL lacks TLSv1_1, log the limitation but keep VALID_TLS."""
        mock_probe.return_value = _make_mock_probe(
            "example.com", "VALID_TLS", tls_version="TLSv1.3",
            deprecated_tls_detected=False, deprecated_tls_check="unavailable_on_platform",
        )
        r = analyze_domain("example.com")
        self.assertEqual(r["tls_probe"]["classification"], "VALID_TLS")
        self.assertEqual(r["tls_probe"]["deprecated_tls_check"], "unavailable_on_platform")
        self.assertIn("unavailable", " ".join(r["tls_probe"]["warnings"]).lower())

    @patch("trustlint.analyzer.probe_domain")
    def test_deprecated_tls_in_json_output(self, mock_probe: MagicMock) -> None:
        """Deprecated TLS fields appear in JSON output."""
        mock_probe.return_value = _make_mock_probe(
            "old.example.com", "VALID_TLS", tls_version="TLSv1.3",
            deprecated_tls_detected=True, deprecated_tls_check="supported",
        )
        r = analyze_domain("old.example.com")
        json_str = format_json_output([r], "balanced")
        parsed = json.loads(json_str)
        tp = parsed["results"][0]["tls_probe"]
        self.assertEqual(tp["classification"], "DEPRECATED_TLS_VERSION")
        self.assertTrue(tp["deprecated_tls_detected"])

    @patch("trustlint.analyzer.probe_domain")
    def test_deprecated_tls_in_structured_text(self, mock_probe: MagicMock) -> None:
        """Deprecated TLS fields appear in console output."""
        mock_probe.return_value = _make_mock_probe(
            "old.example.com", "VALID_TLS", tls_version="TLSv1.3",
            deprecated_tls_detected=True, deprecated_tls_check="supported",
        )
        r = analyze_domain("old.example.com")
        text = format_structured_text(r)
        self.assertIn("Deprecated TLS Check", text)
        self.assertIn("Deprecated TLS Detected", text)


class TestBuildEvidenceArtifact(unittest.TestCase):
    def test_valid_tls_artifact(self) -> None:
        probe = _make_mock_probe("example.com", "VALID_TLS")
        artifact = _build_evidence_artifact("example.com", probe)
        self.assertEqual(artifact["source"], "tls_probe:example.com")
        self.assertEqual(artifact["type"], "tls_certificate")
        self.assertEqual(artifact["data"]["valid"], True)
        self.assertEqual(artifact["data"]["expiry_days"], 89)
        self.assertEqual(artifact["data"]["headers"]["hsts"], None)
        self.assertEqual(artifact["data"]["headers"]["csp"], None)
        self.assertEqual(artifact["data"]["headers"]["hsts_checked"], False)
        self.assertEqual(artifact["data"]["headers"]["csp_checked"], False)
        self.assertEqual(artifact["transport_meta"]["status"], "ok")
        self.assertEqual(artifact["transport_meta"]["latency_ms"], 45.2)

    def test_expired_cert_artifact(self) -> None:
        probe = _make_mock_probe("bad.com", "EXPIRED_CERT", expiry_days=-1, cert_is_expired=True)
        artifact = _build_evidence_artifact("bad.com", probe)
        self.assertEqual(artifact["data"]["valid"], False)
        self.assertEqual(artifact["data"]["expiry_days"], -1)

    def test_timeout_artifact(self) -> None:
        probe = _make_mock_probe("timeout.com", "TIMEOUT")
        artifact = _build_evidence_artifact("timeout.com", probe)
        self.assertEqual(artifact["transport_meta"]["status"], "timeout")

    def test_dns_failure_artifact(self) -> None:
        probe = _make_mock_probe("dnsfail.com", "DNS_FAILURE", dns_error="not found")
        artifact = _build_evidence_artifact("dnsfail.com", probe)
        self.assertEqual(artifact["transport_meta"]["status"], "error")


class TestAnalyzeDomainWithSPL(unittest.TestCase):
    @patch("trustlint.analyzer.probe_domain")
    def test_spl_pipeline_produces_confidence(self, mock_probe: MagicMock) -> None:
        """With --spl active, the untrained pipeline returns 0.5 confidence."""
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")

        from spl_v7.dsl import FeatureDSLProgram
        from spl_v7.kafka_pipeline import EvidencePipeline

        program = FeatureDSLProgram.from_text(
            "feature tls_valid = data.valid\n"
            "feature tls_expiry_urgency = normalize(30 - data.expiry_days, 0, 30)\n"
        )
        pipeline = EvidencePipeline(feature_program=program)

        r = analyze_domain("example.com", profile="balanced", spl_pipeline=pipeline)

        self.assertTrue(r["spl_active"])
        self.assertIsNotNone(r["spl"]["decision"])
        self.assertGreaterEqual(r["spl"]["confidence"], 0.0)
        self.assertLessEqual(r["spl"]["confidence"], 1.0)
        self.assertEqual(r["spl"]["weakness_flags"], [])

    @patch("trustlint.analyzer.probe_domain")
    def test_spl_confidence_untrained_is_05(self, mock_probe: MagicMock) -> None:
        """Untrained model with zero weights → logit=0 → sigmoid=0.5."""
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")

        from spl_v7.dsl import FeatureDSLProgram
        from spl_v7.kafka_pipeline import EvidencePipeline

        program = FeatureDSLProgram.from_text(
            "feature tls_valid = data.valid\n"
        )
        pipeline = EvidencePipeline(feature_program=program)
        r = analyze_domain("example.com", profile="balanced", spl_pipeline=pipeline)

        self.assertAlmostEqual(r["spl"]["confidence"], 0.5, places=6)

    @patch("trustlint.analyzer.probe_domain")
    def test_spl_changes_decision_source(self, mock_probe: MagicMock) -> None:
        """With SPL active, decision source is COMBINED instead of ADAPTER_FALLBACK."""
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")

        from spl_v7.dsl import FeatureDSLProgram
        from spl_v7.kafka_pipeline import EvidencePipeline

        program = FeatureDSLProgram.from_text(
            "feature tls_valid = data.valid\n"
        )
        pipeline = EvidencePipeline(feature_program=program)
        r = analyze_domain("example.com", profile="balanced", spl_pipeline=pipeline)

        self.assertEqual(r["final"]["source"], "COMBINED")
        self.assertFalse(r["final"]["fallback_used"])

    @patch("trustlint.analyzer.probe_domain")
    def test_spl_active_in_json_metadata(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")

        from spl_v7.dsl import FeatureDSLProgram
        from spl_v7.kafka_pipeline import EvidencePipeline

        program = FeatureDSLProgram.from_text("feature tls_valid = data.valid\n")
        pipeline = EvidencePipeline(feature_program=program)
        r = analyze_domain("example.com", profile="balanced", spl_pipeline=pipeline)
        json_str = format_json_output([r], "balanced")
        parsed = json.loads(json_str)
        self.assertTrue(parsed["metadata"]["spl_active"])

    @patch("trustlint.analyzer.probe_domain")
    def test_spl_inactive_in_json_metadata(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")
        r = analyze_domain("example.com", profile="balanced")
        json_str = format_json_output([r], "balanced")
        parsed = json.loads(json_str)
        self.assertFalse(parsed["metadata"]["spl_active"])

    @patch("trustlint.analyzer.probe_domain")
    def test_spl_markdown_note(self, mock_probe: MagicMock) -> None:
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")

        from spl_v7.dsl import FeatureDSLProgram
        from spl_v7.kafka_pipeline import EvidencePipeline

        program = FeatureDSLProgram.from_text("feature tls_valid = data.valid\n")
        pipeline = EvidencePipeline(feature_program=program)
        r = analyze_domain("example.com", profile="balanced", spl_pipeline=pipeline)
        md = format_markdown_output([r], "balanced")
        self.assertIn("SPL Core active", md)

    @patch("trustlint.analyzer.probe_domain")
    def test_spl_pipeline_error_falls_back(self, mock_probe: MagicMock) -> None:
        """When pipeline processing fails, we fall back gracefully."""
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")

        from unittest.mock import MagicMock
        broken_pipeline = MagicMock()
        broken_pipeline.ingest.side_effect = RuntimeError("pipeline crash")

        r = analyze_domain("example.com", profile="balanced", spl_pipeline=broken_pipeline)

        self.assertTrue(r["spl_active"])
        self.assertEqual(r["spl"]["weakness_flags"], ["pipeline_error"])
        self.assertIsNone(r["spl"]["decision"])
        self.assertEqual(r["spl"]["confidence"], 0.0)

    @patch("trustlint.analyzer.probe_domain")
    def test_spl_with_conservative_profile(self, mock_probe: MagicMock) -> None:
        """With conservative profile, 0.5 confidence < 0.7 threshold → REVIEW."""
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")

        from spl_v7.dsl import FeatureDSLProgram
        from spl_v7.kafka_pipeline import EvidencePipeline

        program = FeatureDSLProgram.from_text("feature tls_valid = data.valid\n")
        pipeline = EvidencePipeline(feature_program=program)
        r = analyze_domain("example.com", profile="conservative", spl_pipeline=pipeline)

        self.assertEqual(r["final"]["decision"], "REVIEW")
        self.assertEqual(r["final"]["risk"], "LOW")

    @patch("trustlint.analyzer.probe_domain")
    def test_spl_with_strict_profile(self, mock_probe: MagicMock) -> None:
        """With strict profile, 0.5 confidence < 0.7 threshold → REVIEW."""
        mock_probe.return_value = _make_mock_probe("example.com", "VALID_TLS")

        from spl_v7.dsl import FeatureDSLProgram
        from spl_v7.kafka_pipeline import EvidencePipeline

        program = FeatureDSLProgram.from_text("feature tls_valid = data.valid\n")
        pipeline = EvidencePipeline(feature_program=program)
        r = analyze_domain("example.com", profile="strict", spl_pipeline=pipeline)

        self.assertEqual(r["final"]["decision"], "REVIEW")


if __name__ == "__main__":
    unittest.main()
