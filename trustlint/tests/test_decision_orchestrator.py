"""Tests for Phase 7 -- Decision Orchestration Policy.

Verifies:
- Schema stability (OrchestratorInput, OrchestratorOutput)
- All 7 decision rules evaluate correctly
- OFE isolation (observational, never affects decisions)
- classify_mismatch: exact/safe/unsafe/under_blocking/over-blocking
- compute_benchmark_results: aggregation correctness with safety metrics
- generate_report: markdown structure with semantic audit sections
- save_results: JSON structure
- Rule priority (first match wins)
- Adapter guardrail: risks cannot become clean ALLOW
- Safety-adjusted conformance (exact + safe)
- Under-blocking classification
- Probe-limited mismatch detection
- REPORT handling semantics
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from collections import Counter

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from decision_orchestrator import (
    decide,
    orchestrate,
    generate_report,
    save_results,
    BenchmarkRunResult,
    OrchestratorInput,
    OrchestratorOutput,
    SEVERITY_ORDER,
    SEVERITY_RANK,
    OperatingProfile,
)
from decision_orchestrator.reporter import (
    classify_mismatch,
    compute_benchmark_results,
    is_probe_limited,
    PROBE_LIMITED_CLASSIFICATION_PAIRS,
)


class TestOrchestratorSchema(unittest.TestCase):
    """Verify schema types are stable."""

    def test_severity_order_is_stable(self) -> None:
        self.assertEqual(SEVERITY_ORDER, ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"])

    def test_severity_rank_maps_correctly(self) -> None:
        self.assertEqual(SEVERITY_RANK["NONE"], 0)
        self.assertEqual(SEVERITY_RANK["LOW"], 1)
        self.assertEqual(SEVERITY_RANK["MEDIUM"], 2)
        self.assertEqual(SEVERITY_RANK["HIGH"], 3)
        self.assertEqual(SEVERITY_RANK["CRITICAL"], 4)

    def test_orchestrator_output_has_required_fields(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            spl_decision=False,
            spl_confidence=0.9,
            classification="VALID_TLS",
        )
        required = [
            "classification", "final_decision", "final_risk",
            "primary_reason", "supporting_reasons", "decision_source",
            "spl_decision", "spl_confidence", "adapter_risk_category",
            "adapter_severity", "adapter_action_hint", "ofe_observed",
            "fallback_used", "confidence_source",
        ]
        for field in required:
            self.assertIn(field, out, f"Missing field: {field}")

    def test_orchestrator_output_types(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            spl_decision=False,
            spl_confidence=0.9,
            classification="VALID_TLS",
        )
        self.assertIsInstance(out["final_decision"], str)
        self.assertIsInstance(out["final_risk"], str)
        self.assertIsInstance(out["primary_reason"], str)
        self.assertIsInstance(out["supporting_reasons"], list)
        self.assertIsInstance(out["spl_confidence"], (int, float))
        self.assertIsInstance(out["ofe_observed"], bool)


class TestDecisionRules(unittest.TestCase):
    """Test all 7 orchestration rules."""

    # Rule 1: CRITICAL severity -> DENY
    def test_rule1_critical_deny(self) -> None:
        out = decide(
            adapter_risk_category="SECURITY_RISK",
            adapter_severity="CRITICAL",
            adapter_action_hint="DENY",
            classification="WRONG_HOST_CERT",
            spl_decision=None,
            spl_confidence=0.0,
        )
        self.assertEqual(out["final_decision"], "DENY")
        self.assertEqual(out["final_risk"], "CRITICAL")
        self.assertEqual(out["decision_source"], "ADAPTER")

    def test_rule1_critical_overrides_spl_allow(self) -> None:
        out = decide(
            adapter_risk_category="SECURITY_RISK",
            adapter_severity="CRITICAL",
            adapter_action_hint="DENY",
            classification="WRONG_HOST_CERT",
            spl_decision=False,
            spl_confidence=0.95,
        )
        self.assertEqual(out["final_decision"], "DENY")
        self.assertIn("CRITICAL", out["primary_reason"])

    # Rule 2: MEDIUM availability -> REVIEW
    def test_rule2_medium_availability_review(self) -> None:
        out = decide(
            adapter_risk_category="AVAILABILITY_RISK",
            adapter_severity="MEDIUM",
            adapter_action_hint="REVIEW",
            classification="DNS_FAILURE",
            spl_decision=None,
            spl_confidence=0.0,
        )
        self.assertEqual(out["final_decision"], "REVIEW")
        self.assertEqual(out["final_risk"], "MEDIUM")
        self.assertEqual(out["decision_source"], "ADAPTER")

    def test_rule2_review_for_all_availability_types(self) -> None:
        for cls in ("DNS_FAILURE", "CONNECTION_ERROR", "TIMEOUT"):
            out = decide(
                adapter_risk_category="AVAILABILITY_RISK",
                adapter_severity="MEDIUM",
                adapter_action_hint="REVIEW",
                classification=cls,
                spl_decision=None,
                spl_confidence=0.0,
            )
            self.assertEqual(out["final_decision"], "REVIEW", f"{cls} should be REVIEW")

    # Rule 3: HIGH severity security -> REVIEW
    def test_rule3_high_security_review(self) -> None:
        for cls in ("EXPIRED_CERT", "SELF_SIGNED_CERT",
                     "UNTRUSTED_CHAIN", "INCOMPLETE_CHAIN",
                     "DEPRECATED_TLS_VERSION"):
            out = decide(
                adapter_risk_category="SECURITY_RISK",
                adapter_severity="HIGH",
                adapter_action_hint="RENEW_OR_DENY",
                classification=cls,
                spl_decision=None,
                spl_confidence=0.0,
            )
            self.assertEqual(out["final_decision"], "REVIEW", f"{cls} should be REVIEW")
            self.assertIn("Security risk", out["primary_reason"], f"{cls} primary_reason: {out['primary_reason']}")

    def test_rule3_security_review_with_spl(self) -> None:
        out = decide(
            adapter_risk_category="SECURITY_RISK",
            adapter_severity="HIGH",
            adapter_action_hint="RENEW_OR_DENY",
            classification="EXPIRED_CERT",
            spl_decision=False,
            spl_confidence=0.8,
        )
        self.assertEqual(out["final_decision"], "REVIEW")
        self.assertIn("REVIEW", out["final_decision"])
        self.assertIn("supporting_reasons", out)
        spl_in_reasons = any("SPL" in r for r in out["supporting_reasons"])
        self.assertTrue(spl_in_reasons, "SPL should appear in supporting_reasons")

    # Rule 4: AMBIGUOUS -> REVIEW
    def test_rule4_ambiguous_review(self) -> None:
        for cls in ("TLS_HANDSHAKE_FAILURE", "UNKNOWN_SSL_ERROR"):
            out = decide(
                adapter_risk_category="AMBIGUOUS_FAILURE",
                adapter_severity="MEDIUM",
                adapter_action_hint="INVESTIGATE",
                classification=cls,
                spl_decision=None,
                spl_confidence=0.0,
            )
            self.assertEqual(out["final_decision"], "REVIEW", f"{cls} should be REVIEW")

    def test_rule4_tls_handshake_medium(self) -> None:
        out = decide(
            adapter_risk_category="AMBIGUOUS_FAILURE",
            adapter_severity="MEDIUM",
            adapter_action_hint="INVESTIGATE",
            classification="TLS_HANDSHAKE_FAILURE",
            spl_decision=None,
            spl_confidence=0.0,
        )
        self.assertEqual(out["final_risk"], "MEDIUM")

    def test_rule4_unknown_ssl_low(self) -> None:
        out = decide(
            adapter_risk_category="UNKNOWN_RISK",
            adapter_severity="LOW",
            adapter_action_hint="INVESTIGATE",
            classification="UNKNOWN_SSL_ERROR",
            spl_decision=None,
            spl_confidence=0.0,
        )
        self.assertEqual(out["final_risk"], "LOW")

    # Rule 5: VALID_TLS + SPL high confidence -> ALLOW
    def test_rule5_valid_tls_high_conf_allow(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
            spl_confidence=0.9,
        )
        self.assertEqual(out["final_decision"], "ALLOW")
        self.assertEqual(out["final_risk"], "NONE")
        self.assertIn("SPL", out["decision_source"])

    def test_rule5_high_conf_at_threshold(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
            spl_confidence=0.5,
        )
        self.assertEqual(out["final_decision"], "ALLOW")

    def test_rule5_spl_none_does_not_trigger_allow_conservative(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=None,
            spl_confidence=0.0,
            profile="conservative",
        )
        self.assertNotEqual(out["final_decision"], "ALLOW")

    # Rule 6: VALID_TLS + SPL low confidence -> REVIEW
    def test_rule6_valid_tls_low_conf_review(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
            spl_confidence=0.3,
        )
        self.assertEqual(out["final_decision"], "REVIEW")
        self.assertEqual(out["decision_source"], "CONFIDENCE")

    def test_rule6_valid_tls_no_spl_conservative_review(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=None,
            spl_confidence=0.0,
            profile="conservative",
        )
        self.assertEqual(out["final_decision"], "REVIEW")
        self.assertIn("SPL confidence is unavailable", out["primary_reason"])

    def test_rule6_just_below_threshold(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
            spl_confidence=0.4999,
        )
        self.assertEqual(out["final_decision"], "REVIEW")

    # Rule 7: Fallback -> REVIEW
    def test_rule7_fallback_review(self) -> None:
        out = decide(
            adapter_risk_category="SOME_UNKNOWN_RISK",
            adapter_severity="LOW",
            adapter_action_hint="INVESTIGATE",
            classification="SOME_UNKNOWN_CLASSIFICATION",
            spl_decision=None,
            spl_confidence=0.0,
        )
        self.assertEqual(out["final_decision"], "REVIEW")
        self.assertIn("Unhandled", out["primary_reason"])


class TestConfidenceFallback(unittest.TestCase):
    """Fallback ALLOW rules when SPL confidence is unavailable."""

    def test_balanced_fallback_allows_clean_valid_tls(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=None,
            spl_confidence=0.0,
            profile="balanced",
            probe_limited=False,
        )
        self.assertEqual(out["final_decision"], "ALLOW")
        self.assertEqual(out["decision_source"], "ADAPTER_FALLBACK")
        self.assertTrue(out["fallback_used"])
        self.assertEqual(out["confidence_source"], "FALLBACK")
        self.assertEqual(out["final_risk"], "NONE")

    def test_conservative_fallback_reviews_clean_valid_tls(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=None,
            spl_confidence=0.0,
            profile="conservative",
            probe_limited=False,
        )
        self.assertEqual(out["final_decision"], "REVIEW")
        self.assertEqual(out["confidence_source"], "UNAVAILABLE")

    def test_strict_fallback_reviews_clean_valid_tls(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=None,
            spl_confidence=0.0,
            profile="strict",
            probe_limited=False,
        )
        self.assertEqual(out["final_decision"], "REVIEW")
        self.assertEqual(out["confidence_source"], "UNAVAILABLE")

    def test_expired_cert_never_allow_via_fallback(self) -> None:
        for profile in ("balanced", "conservative", "strict"):
            out = decide(
                adapter_risk_category="SECURITY_RISK",
                adapter_severity="HIGH",
                adapter_action_hint="RENEW_OR_DENY",
                classification="EXPIRED_CERT",
                spl_decision=None,
                spl_confidence=0.0,
                profile=profile,
            )
            self.assertNotEqual(out["final_decision"], "ALLOW", f"{profile} should not ALLOW expired cert")

    def test_wrong_host_cert_never_allow_via_fallback(self) -> None:
        for profile in ("balanced", "conservative", "strict"):
            out = decide(
                adapter_risk_category="SECURITY_RISK",
                adapter_severity="CRITICAL",
                adapter_action_hint="DENY",
                classification="WRONG_HOST_CERT",
                spl_decision=None,
                spl_confidence=0.0,
                profile=profile,
            )
            self.assertEqual(out["final_decision"], "DENY", f"{profile} should DENY wrong host cert")

    def test_self_signed_cert_never_allow_via_fallback(self) -> None:
        for profile in ("balanced", "conservative", "strict"):
            out = decide(
                adapter_risk_category="SECURITY_RISK",
                adapter_severity="HIGH",
                adapter_action_hint="RENEW_OR_DENY",
                classification="SELF_SIGNED_CERT",
                spl_decision=None,
                spl_confidence=0.0,
                profile=profile,
            )
            self.assertNotEqual(out["final_decision"], "ALLOW", f"{profile} should not ALLOW self-signed cert")

    def test_dns_failure_stays_review_via_fallback(self) -> None:
        out = decide(
            adapter_risk_category="AVAILABILITY_RISK",
            adapter_severity="MEDIUM",
            adapter_action_hint="REVIEW",
            classification="DNS_FAILURE",
            spl_decision=None,
            spl_confidence=0.0,
            profile="balanced",
        )
        self.assertEqual(out["final_decision"], "REVIEW")

    def test_timeout_stays_review_via_fallback(self) -> None:
        out = decide(
            adapter_risk_category="AVAILABILITY_RISK",
            adapter_severity="MEDIUM",
            adapter_action_hint="REVIEW",
            classification="TIMEOUT",
            spl_decision=None,
            spl_confidence=0.0,
            profile="balanced",
        )
        self.assertEqual(out["final_decision"], "REVIEW")

    def test_ambiguous_stays_review_via_fallback(self) -> None:
        out = decide(
            adapter_risk_category="AMBIGUOUS_FAILURE",
            adapter_severity="MEDIUM",
            adapter_action_hint="INVESTIGATE",
            classification="TLS_HANDSHAKE_FAILURE",
            spl_decision=None,
            spl_confidence=0.0,
            profile="balanced",
        )
        self.assertEqual(out["final_decision"], "REVIEW")

    def test_fallback_not_used_when_spl_available(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
            spl_confidence=0.9,
            profile="balanced",
        )
        self.assertFalse(out["fallback_used"])
        self.assertEqual(out["confidence_source"], "SPL")

    def test_fallback_not_used_when_not_valid_tls(self) -> None:
        out = decide(
            adapter_risk_category="AVAILABILITY_RISK",
            adapter_severity="MEDIUM",
            adapter_action_hint="REVIEW",
            classification="DNS_FAILURE",
            spl_decision=None,
            spl_confidence=0.0,
            profile="balanced",
        )
        self.assertFalse(out["fallback_used"])

    def test_probe_limited_prevents_fallback_allow(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=None,
            spl_confidence=0.0,
            profile="balanced",
            probe_limited=True,
        )
        self.assertEqual(out["final_decision"], "REVIEW")
        self.assertFalse(out["fallback_used"])
        self.assertIn("probe limited", out["primary_reason"].lower())

    def test_balanced_fallback_not_allowed_if_adapter_not_clean(self) -> None:
        out = decide(
            adapter_risk_category="AVAILABILITY_RISK",
            adapter_severity="LOW",
            adapter_action_hint="REVIEW",
            classification="VALID_TLS",
            spl_decision=None,
            spl_confidence=0.0,
            profile="balanced",
            probe_limited=False,
        )
        self.assertEqual(out["final_decision"], "REVIEW")
        self.assertFalse(out["fallback_used"])

    def test_no_ofe_influence_on_fallback(self) -> None:
        with_ofe = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=None,
            spl_confidence=0.0,
            profile="balanced",
            ofe_signals={"connection_rtt": 0.05},
        )
        without_ofe = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=None,
            spl_confidence=0.0,
            profile="balanced",
        )
        self.assertEqual(with_ofe["final_decision"], without_ofe["final_decision"])
        self.assertTrue(with_ofe["fallback_used"])
        self.assertTrue(without_ofe["fallback_used"])

    def test_confidence_source_spl_available(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
            spl_confidence=0.9,
            profile="balanced",
        )
        self.assertEqual(out["confidence_source"], "SPL")

    def test_confidence_source_unavailable_adapter_only(self) -> None:
        out = decide(
            adapter_risk_category="SECURITY_RISK",
            adapter_severity="HIGH",
            adapter_action_hint="RENEW_OR_DENY",
            classification="EXPIRED_CERT",
            spl_decision=None,
            spl_confidence=0.0,
            profile="balanced",
        )
        self.assertEqual(out["confidence_source"], "UNAVAILABLE")


class TestRulePriority(unittest.TestCase):
    """First matching rule wins."""

    def test_critical_wins_over_ambiguous(self) -> None:
        out = decide(
            adapter_risk_category="SECURITY_RISK",
            adapter_severity="CRITICAL",
            adapter_action_hint="DENY",
            classification="TLS_HANDSHAKE_FAILURE",
            spl_decision=False,
            spl_confidence=0.9,
        )
        self.assertEqual(out["final_decision"], "DENY")

    def test_availability_blocks_valid_tls_with_spl(self) -> None:
        out = decide(
            adapter_risk_category="AVAILABILITY_RISK",
            adapter_severity="MEDIUM",
            adapter_action_hint="REVIEW",
            classification="DNS_FAILURE",
            spl_decision=False,
            spl_confidence=0.95,
        )
        self.assertEqual(out["final_decision"], "REVIEW")


class TestOFEIsolation(unittest.TestCase):
    """OFE is observational only, never affects final decision."""

    def test_ofe_with_signals_still_allows(self) -> None:
        no_ofe = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
            spl_confidence=0.9,
        )
        with_ofe = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
            spl_confidence=0.9,
            ofe_signals={"connection_rtt": 0.05, "cert_age_days": 30},
        )
        self.assertEqual(no_ofe["final_decision"], with_ofe["final_decision"])

    def test_ofe_observed_flag_set(self) -> None:
        out_no = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
            spl_confidence=0.9,
        )
        out_yes = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
            spl_confidence=0.9,
            ofe_signals={"connection_rtt": 0.05},
        )
        self.assertFalse(out_no["ofe_observed"])
        self.assertTrue(out_yes["ofe_observed"])

    def test_ofe_empty_dict_not_observed(self) -> None:
        out = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
            spl_confidence=0.9,
            ofe_signals={},
        )
        self.assertFalse(out["ofe_observed"])

    def test_ofe_signals_dont_change_deny(self) -> None:
        out = decide(
            adapter_risk_category="SECURITY_RISK",
            adapter_severity="CRITICAL",
            adapter_action_hint="DENY",
            classification="WRONG_HOST_CERT",
            spl_decision=None,
            spl_confidence=0.0,
            ofe_signals={"connection_rtt": 0.05},
        )
        self.assertEqual(out["final_decision"], "DENY")


class TestOrchestrateWrapper(unittest.TestCase):
    """Convenience wrapper unpacks dict correctly."""

    def test_orchestrate_with_valid_input(self) -> None:
        inp: OrchestratorInput = {
            "classification": "VALID_TLS",
            "adapter_risk_category": "ACCEPTABLE_TLS",
            "adapter_severity": "NONE",
            "adapter_action_hint": "NONE",
            "spl_decision": False,
            "spl_confidence": 0.9,
        }
        out = orchestrate(inp)
        self.assertEqual(out["final_decision"], "ALLOW")

    def test_orchestrate_with_partial_input(self) -> None:
        inp: OrchestratorInput = {
            "classification": "EXPIRED_CERT",
            "adapter_risk_category": "SECURITY_RISK",
            "adapter_severity": "HIGH",
            "adapter_action_hint": "RENEW_OR_DENY",
        }
        out = orchestrate(inp)
        self.assertEqual(out["final_decision"], "REVIEW")
        self.assertIsNone(out["spl_decision"])
        self.assertEqual(out["spl_confidence"], 0.0)

    def test_orchestrate_with_weakness_flags(self) -> None:
        inp: OrchestratorInput = {
            "classification": "VALID_TLS",
            "adapter_risk_category": "ACCEPTABLE_TLS",
            "adapter_severity": "NONE",
            "adapter_action_hint": "NONE",
            "spl_decision": False,
            "spl_confidence": 0.9,
            "weakness_flags": ["HSTS_MISSING"],
        }
        out = orchestrate(inp)
        self.assertEqual(out["final_decision"], "ALLOW")


class TestMismatchClassification(unittest.TestCase):
    """classify_mismatch returns correct labels."""

    def test_exact_allow(self) -> None:
        self.assertEqual(classify_mismatch("ACCEPTABLE_TLS", "ALLOW"), "exact")

    def test_exact_deny(self) -> None:
        self.assertEqual(classify_mismatch("SECURITY_RISK", "DENY"), "exact")

    def test_exact_review(self) -> None:
        self.assertEqual(classify_mismatch("AVAILABILITY_RISK", "REVIEW"), "exact")

    def test_exact_review_ambiguous(self) -> None:
        self.assertEqual(classify_mismatch("AMBIGUOUS_FAILURE", "REVIEW"), "exact")

    def test_safe_deny_to_review(self) -> None:
        self.assertEqual(classify_mismatch("SECURITY_RISK", "REVIEW"), "safe")

    def test_safe_deny_to_review_deprecated(self) -> None:
        self.assertEqual(classify_mismatch("DEPRECATED_PROTOCOL_RISK", "REVIEW"), "safe")

    def test_unsafe_deny_to_allow(self) -> None:
        self.assertEqual(classify_mismatch("SECURITY_RISK", "ALLOW"), "unsafe")

    def test_unsafe_deprecated_to_allow(self) -> None:
        self.assertEqual(classify_mismatch("DEPRECATED_PROTOCOL_RISK", "ALLOW"), "unsafe")

    def test_under_blocking_review_to_allow(self) -> None:
        self.assertEqual(classify_mismatch("AVAILABILITY_RISK", "ALLOW"), "under_blocking")

    def test_over_blocking_allow_to_deny(self) -> None:
        self.assertEqual(classify_mismatch("ACCEPTABLE_TLS", "DENY"), "over_blocking")

    def test_over_blocking_allow_to_review(self) -> None:
        self.assertEqual(classify_mismatch("ACCEPTABLE_TLS", "REVIEW"), "over_blocking")

    def test_unknown_expected(self) -> None:
        self.assertEqual(classify_mismatch(None, "ALLOW"), "unknown")

    def test_unknown_expected_policy_value(self) -> None:
        self.assertEqual(classify_mismatch("SOME_UNKNOWN_POLICY", "ALLOW"), "unknown")


class TestBenchmarkResults(unittest.TestCase):
    """compute_benchmark_results aggregation."""

    def test_all_exact(self) -> None:
        results = [
            {"domain": "a.com", "classification": "VALID_TLS",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "ALLOW"},
            {"domain": "b.com", "classification": "EXPIRED_CERT",
             "expected_policy": "SECURITY_RISK", "final_decision": "DENY"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        self.assertEqual(br["total"], 2)
        self.assertEqual(br["exact_matches"], 2)
        self.assertEqual(br["conformance_pct"], 100.0)
        self.assertEqual(br["decision_distribution"], {"ALLOW": 1, "DENY": 1})

    def test_mixed_mismatches(self) -> None:
        results = [
            {"domain": "a.com", "classification": "VALID_TLS",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "ALLOW"},
            {"domain": "b.com", "classification": "EXPIRED_CERT",
             "expected_policy": "SECURITY_RISK", "final_decision": "ALLOW"},
            {"domain": "c.com", "classification": "DNS_FAILURE",
             "expected_policy": "AVAILABILITY_RISK", "final_decision": "REVIEW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        self.assertEqual(br["total"], 3)
        self.assertEqual(br["exact_matches"], 2)
        self.assertEqual(br["unsafe_mismatches"], 1)
        self.assertEqual(br["safe_mismatches"], 0)
        self.assertEqual(br["under_blocking"], 0)
        self.assertEqual(br["conformance_pct"], 66.7)

    def test_none_expected(self) -> None:
        results = [
            {"domain": "a.com", "classification": "VALID_TLS",
             "expected_policy": None, "final_decision": "ALLOW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        self.assertEqual(br["total"], 1)
        self.assertEqual(br["exact_matches"], 0)
        self.assertEqual(len(br["mismatches"]), 0)

    def test_empty_results(self) -> None:
        br = compute_benchmark_results([], "test-mode", "empty")
        self.assertEqual(br["total"], 0)
        self.assertEqual(br["conformance_pct"], 0.0)

    def test_benchmark_result_has_required_keys(self) -> None:
        results = [
            {"domain": "a.com", "classification": "VALID_TLS",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "ALLOW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        required = ["mode", "description", "total", "exact_matches",
                     "safe_mismatches", "unsafe_mismatches", "over_blocking",
                     "decision_distribution", "conformance_pct", "mismatches"]
        for key in required:
            self.assertIn(key, br, f"Missing key: {key}")


class TestReportGeneration(unittest.TestCase):
    """generate_report produces correct markdown."""

    def test_report_contains_mode_names(self) -> None:
        br1 = compute_benchmark_results([], "mode-a", "desc-a")
        br2 = compute_benchmark_results([], "mode-b", "desc-b")
        report = generate_report({"mode-a": br1, "mode-b": br2}, "/tmp")
        self.assertIn("mode-a", report)
        self.assertIn("mode-b", report)

    def test_report_contains_sections(self) -> None:
        br = compute_benchmark_results([], "test-mode", "test")
        report = generate_report({"test-mode": br}, "/tmp")
        sections = [
            "Decision Orchestration Policy Benchmark Report",
            "Baseline Definitions",
            "Overall Comparison",
            "Decision Distribution",
            "Risk Distribution",
            "Limitations",
        ]
        for s in sections:
            self.assertIn(s, report, f"Missing section: {s}")

    def test_report_highlights_unsafe_mismatches(self) -> None:
        results = [
            {"domain": "bad.com", "classification": "EXPIRED_CERT",
             "expected_policy": "SECURITY_RISK", "final_decision": "ALLOW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        report = generate_report({"test-mode": br}, "/tmp")
        self.assertIn("Unsafe Mismatches", report)
        self.assertIn("bad.com", report)

    def test_report_highlights_over_blocking(self) -> None:
        results = [
            {"domain": "good.com", "classification": "VALID_TLS",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "REVIEW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        report = generate_report({"test-mode": br}, "/tmp")
        self.assertIn("Over-blocking", report)
        self.assertIn("good.com", report)

    def test_report_no_unsafe_mention_when_none(self) -> None:
        br = compute_benchmark_results([], "test-mode", "test")
        report = generate_report({"test-mode": br}, "/tmp")
        self.assertIn("No unsafe mismatches", report)


class TestSaveResults(unittest.TestCase):
    """save_results produces valid JSON."""

    def test_save_results_creates_file(self) -> None:
        br = compute_benchmark_results([], "test-mode", "test")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            save_results({"test-mode": br}, path)
            self.assertTrue(os.path.isfile(path))
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("_metadata", data)
            self.assertIn("results", data)
            self.assertFalse(data["_metadata"]["spl_core_modified"])
            self.assertEqual(data["_metadata"]["ofe_status"], "HOLD_PENDING_REAL_DATA")
        finally:
            if os.path.isfile(path):
                os.unlink(path)


class TestIntegrationWithAdapter(unittest.TestCase):
    """End-to-end: adapter + orchestrator work together."""

    def test_adapter_critical_propagates_to_deny(self) -> None:
        from tls_policy_adapter import classify_risk
        ev = classify_risk("WRONG_HOST_CERT")
        self.assertEqual(ev.severity, "CRITICAL")
        out = decide(
            adapter_risk_category=ev.risk_category,
            adapter_severity=ev.severity,
            adapter_action_hint=ev.action_hint,
            classification="WRONG_HOST_CERT",
            spl_decision=None,
            spl_confidence=0.0,
        )
        self.assertEqual(out["final_decision"], "DENY")

    def test_adapter_valid_tls_with_high_spl_allows(self) -> None:
        from tls_policy_adapter import classify_risk
        ev = classify_risk("VALID_TLS")
        self.assertEqual(ev.severity, "NONE")
        out = decide(
            adapter_risk_category=ev.risk_category,
            adapter_severity=ev.severity,
            adapter_action_hint=ev.action_hint,
            classification="VALID_TLS",
            spl_decision=False,
            spl_confidence=0.95,
        )
        self.assertEqual(out["final_decision"], "ALLOW")

    def test_adapter_expired_cert_propagates_to_review(self) -> None:
        from tls_policy_adapter import classify_risk
        ev = classify_risk("EXPIRED_CERT")
        self.assertEqual(ev.severity, "HIGH")
        out = decide(
            adapter_risk_category=ev.risk_category,
            adapter_severity=ev.severity,
            adapter_action_hint=ev.action_hint,
            classification="EXPIRED_CERT",
            spl_decision=None,
            spl_confidence=0.0,
        )
        self.assertEqual(out["final_decision"], "REVIEW")


class TestAdapterGuardrail(unittest.TestCase):
    """Guardrail: adapter-level risks must prevent clean ALLOW."""

    def test_expired_cert_cannot_become_allow_without_spl(self) -> None:
        out = decide(
            adapter_risk_category="SECURITY_RISK",
            adapter_severity="HIGH",
            adapter_action_hint="RENEW_OR_DENY",
            classification="EXPIRED_CERT",
            spl_decision=None,
            spl_confidence=0.0,
        )
        self.assertNotEqual(out["final_decision"], "ALLOW")

    def test_expired_cert_cannot_become_allow_with_high_spl(self) -> None:
        out = decide(
            adapter_risk_category="SECURITY_RISK",
            adapter_severity="HIGH",
            adapter_action_hint="RENEW_OR_DENY",
            classification="EXPIRED_CERT",
            spl_decision=False,
            spl_confidence=0.95,
        )
        self.assertNotEqual(out["final_decision"], "ALLOW")

    def test_wrong_host_cert_cannot_become_allow(self) -> None:
        out = decide(
            adapter_risk_category="SECURITY_RISK",
            adapter_severity="CRITICAL",
            adapter_action_hint="DENY",
            classification="WRONG_HOST_CERT",
            spl_decision=False,
            spl_confidence=0.95,
        )
        self.assertEqual(out["final_decision"], "DENY")

    def test_self_signed_cert_cannot_become_clean_allow(self) -> None:
        out = decide(
            adapter_risk_category="SECURITY_RISK",
            adapter_severity="HIGH",
            adapter_action_hint="REVIEW_OR_DENY",
            classification="SELF_SIGNED_CERT",
            spl_decision=False,
            spl_confidence=0.8,
        )
        self.assertNotEqual(out["final_decision"], "ALLOW")

    def test_untrusted_chain_cannot_become_clean_allow(self) -> None:
        out = decide(
            adapter_risk_category="SECURITY_RISK",
            adapter_severity="HIGH",
            adapter_action_hint="REVIEW_OR_DENY",
            classification="UNTRUSTED_CHAIN",
            spl_decision=False,
            spl_confidence=0.9,
        )
        self.assertNotEqual(out["final_decision"], "ALLOW")

    def test_deprecated_tls_cannot_become_clean_allow(self) -> None:
        out = decide(
            adapter_risk_category="DEPRECATED_PROTOCOL_RISK",
            adapter_severity="HIGH",
            adapter_action_hint="MODERNIZE_OR_DENY",
            classification="DEPRECATED_TLS_VERSION",
            spl_decision=False,
            spl_confidence=0.9,
        )
        self.assertNotEqual(out["final_decision"], "ALLOW")

    def test_timeout_maps_to_review_not_allow(self) -> None:
        out = decide(
            adapter_risk_category="AVAILABILITY_RISK",
            adapter_severity="MEDIUM",
            adapter_action_hint="REVIEW",
            classification="TIMEOUT",
            spl_decision=None,
            spl_confidence=0.0,
        )
        self.assertEqual(out["final_decision"], "REVIEW")

    def test_dns_failure_maps_to_review_not_allow(self) -> None:
        out = decide(
            adapter_risk_category="AVAILABILITY_RISK",
            adapter_severity="MEDIUM",
            adapter_action_hint="REVIEW",
            classification="DNS_FAILURE",
            spl_decision=None,
            spl_confidence=0.0,
        )
        self.assertEqual(out["final_decision"], "REVIEW")

    def test_valid_tls_allow_only_with_high_confidence(self) -> None:
        out_low = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=None,
            spl_confidence=0.0,
            profile="conservative",
        )
        self.assertNotEqual(out_low["final_decision"], "ALLOW")
        out_high = decide(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
            spl_confidence=0.9,
            profile="conservative",
        )
        self.assertEqual(out_high["final_decision"], "ALLOW")


class TestMismatchUnderBlocking(unittest.TestCase):
    """Under-blocking: expected REVIEW but got ALLOW."""

    def test_under_blocking_availability(self) -> None:
        self.assertEqual(
            classify_mismatch("AVAILABILITY_RISK", "ALLOW"),
            "under_blocking",
        )

    def test_under_blocking_ambiguous(self) -> None:
        self.assertEqual(
            classify_mismatch("AMBIGUOUS_FAILURE", "ALLOW"),
            "under_blocking",
        )

    def test_under_blocking_chain_trust(self) -> None:
        self.assertEqual(
            classify_mismatch("CHAIN_TRUST_FAILURE", "ALLOW"),
            "under_blocking",
        )

    def test_under_blocking_unknown(self) -> None:
        self.assertEqual(
            classify_mismatch("UNKNOWN_RISK", "ALLOW"),
            "under_blocking",
        )


class TestProbeLimitedDetection(unittest.TestCase):
    """is_probe_limited detects probe-level limitations."""

    def test_dns_on_acceptable_tls(self) -> None:
        self.assertTrue(is_probe_limited("DNS_FAILURE", "ACCEPTABLE_TLS"))

    def test_valid_tls_on_security_risk(self) -> None:
        self.assertTrue(is_probe_limited("VALID_TLS", "SECURITY_RISK"))

    def test_valid_tls_on_deprecated(self) -> None:
        self.assertTrue(is_probe_limited("VALID_TLS", "DEPRECATED_PROTOCOL_RISK"))

    def test_expired_cert_not_probe_limited(self) -> None:
        self.assertFalse(is_probe_limited("EXPIRED_CERT", "SECURITY_RISK"))

    def test_none_expected_not_limited(self) -> None:
        self.assertFalse(is_probe_limited("VALID_TLS", None))

    def test_pairs_are_known_set(self) -> None:
        self.assertIn(("DNS_FAILURE", "ACCEPTABLE_TLS"), PROBE_LIMITED_CLASSIFICATION_PAIRS)
        self.assertIn(("VALID_TLS", "SECURITY_RISK"), PROBE_LIMITED_CLASSIFICATION_PAIRS)
        self.assertIn(("VALID_TLS", "DEPRECATED_PROTOCOL_RISK"), PROBE_LIMITED_CLASSIFICATION_PAIRS)


class TestSafetyAdjustedScoring(unittest.TestCase):
    """Safety-adjusted metrics from compute_benchmark_results."""

    def test_safety_adjusted_all_exact(self) -> None:
        results = [
            {"domain": "a.com", "classification": "VALID_TLS",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "ALLOW"},
            {"domain": "b.com", "classification": "DNS_FAILURE",
             "expected_policy": "AVAILABILITY_RISK", "final_decision": "REVIEW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        self.assertEqual(br["conformance_pct"], 100.0)
        self.assertEqual(br["safety_adjusted_pct"], 100.0)

    def test_safety_adjusted_with_safe_mismatches(self) -> None:
        results = [
            {"domain": "a.com", "classification": "VALID_TLS",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "ALLOW"},
            {"domain": "b.com", "classification": "EXPIRED_CERT",
             "expected_policy": "SECURITY_RISK", "final_decision": "REVIEW"},
            {"domain": "c.com", "classification": "SELF_SIGNED_CERT",
             "expected_policy": "SECURITY_RISK", "final_decision": "REVIEW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        self.assertEqual(br["exact_matches"], 1)
        self.assertEqual(br["safe_mismatches"], 2)
        self.assertEqual(br["conformance_pct"], 33.3)
        self.assertEqual(br["safety_adjusted_pct"], 100.0)

    def test_safety_adjusted_counts_unsafe_as_not_safe(self) -> None:
        results = [
            {"domain": "a.com", "classification": "EXPIRED_CERT",
             "expected_policy": "SECURITY_RISK", "final_decision": "ALLOW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        self.assertEqual(br["exact_matches"], 0)
        self.assertEqual(br["unsafe_mismatches"], 1)
        self.assertEqual(br["safety_adjusted_pct"], 0.0)

    def test_safety_adjusted_with_all_mismatch_types(self) -> None:
        results = [
            {"domain": "good.com", "classification": "VALID_TLS",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "ALLOW"},
            {"domain": "safe.com", "classification": "EXPIRED_CERT",
             "expected_policy": "SECURITY_RISK", "final_decision": "REVIEW"},
            {"domain": "bad.com", "classification": "WRONG_HOST_CERT",
             "expected_policy": "SECURITY_RISK", "final_decision": "ALLOW"},
            {"domain": "under.com", "classification": "DNS_FAILURE",
             "expected_policy": "AVAILABILITY_RISK", "final_decision": "ALLOW"},
            {"domain": "over.com", "classification": "VALID_TLS",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "REVIEW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        self.assertEqual(br["exact_matches"], 1)
        self.assertEqual(br["safe_mismatches"], 1)
        self.assertEqual(br["unsafe_mismatches"], 1)
        self.assertEqual(br["under_blocking"], 1)
        self.assertEqual(br["over_blocking"], 1)
        self.assertEqual(br["conformance_pct"], 20.0)
        self.assertEqual(br["safety_adjusted_pct"], 40.0)

    def test_safety_adjusted_result_has_new_keys(self) -> None:
        br = compute_benchmark_results([], "test-mode", "test")
        for key in ("safety_adjusted_pct", "under_blocking", "probe_limited",
                     "allow_rate", "review_rate", "deny_rate"):
            self.assertIn(key, br, f"Missing safety key: {key}")

    def test_rates_sum_to_100(self) -> None:
        results = [
            {"domain": "a.com", "classification": "VALID_TLS",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "ALLOW"},
            {"domain": "b.com", "classification": "DNS_FAILURE",
             "expected_policy": "AVAILABILITY_RISK", "final_decision": "REVIEW"},
            {"domain": "c.com", "classification": "WRONG_HOST_CERT",
             "expected_policy": "SECURITY_RISK", "final_decision": "DENY"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        total_rate = br["allow_rate"] + br["review_rate"] + br["deny_rate"]
        self.assertGreaterEqual(total_rate, 98.0)
        self.assertLessEqual(total_rate, 101.0)


class TestProbeLimitedScoring(unittest.TestCase):
    """Probe-limited mismatches tracked in compute_benchmark_results."""

    def test_probe_limited_dns_counted(self) -> None:
        results = [
            {"domain": "columbia.edu", "classification": "DNS_FAILURE",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "REVIEW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        self.assertEqual(br["probe_limited"], 1)
        self.assertEqual(br["over_blocking"], 1)

    def test_probe_limited_deprecated_tls_counted(self) -> None:
        results = [
            {"domain": "tls-v1-0.badssl.com", "classification": "VALID_TLS",
             "expected_policy": "SECURITY_RISK", "final_decision": "ALLOW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        self.assertEqual(br["probe_limited"], 1)
        self.assertEqual(br["unsafe_mismatches"], 1)

    def test_non_probe_limited_not_counted(self) -> None:
        results = [
            {"domain": "expired.badssl.com", "classification": "EXPIRED_CERT",
             "expected_policy": "SECURITY_RISK", "final_decision": "REVIEW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        self.assertEqual(br["probe_limited"], 0)

    def test_exact_match_not_probe_limited(self) -> None:
        results = [
            {"domain": "google.com", "classification": "VALID_TLS",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "ALLOW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        self.assertEqual(br["probe_limited"], 0)


class TestREVIEWHandlingSemantics(unittest.TestCase):
    """REVIEW outcome semantics are clearly defined."""

    def test_review_for_security_risk_is_safe_not_exact(self) -> None:
        mm = classify_mismatch("SECURITY_RISK", "REVIEW")
        self.assertEqual(mm, "safe")
        self.assertNotEqual(mm, "exact")

    def test_review_for_availability_risk_is_exact(self) -> None:
        mm = classify_mismatch("AVAILABILITY_RISK", "REVIEW")
        self.assertEqual(mm, "exact")

    def test_review_for_acceptable_tls_is_over_blocking(self) -> None:
        mm = classify_mismatch("ACCEPTABLE_TLS", "REVIEW")
        self.assertEqual(mm, "over_blocking")

    def test_deny_for_acceptable_tls_is_over_blocking(self) -> None:
        mm = classify_mismatch("ACCEPTABLE_TLS", "DENY")
        self.assertEqual(mm, "over_blocking")

    def test_allow_for_security_risk_is_unsafe(self) -> None:
        mm = classify_mismatch("SECURITY_RISK", "ALLOW")
        self.assertEqual(mm, "unsafe")

    def test_allow_for_deprecated_protocol_is_unsafe(self) -> None:
        mm = classify_mismatch("DEPRECATED_PROTOCOL_RISK", "ALLOW")
        self.assertEqual(mm, "unsafe")


class TestReportSecurityAuditSection(unittest.TestCase):
    """generate_report includes semantic audit sections."""

    def test_report_contains_semantic_audit_summary(self) -> None:
        br = compute_benchmark_results([], "test-mode", "test")
        report = generate_report({"test-mode": br}, "/tmp")
        self.assertIn("Semantic Audit Summary", report)

    def test_report_contains_safety_adjusted(self) -> None:
        br = compute_benchmark_results([], "test-mode", "test")
        report = generate_report({"test-mode": br}, "/tmp")
        self.assertIn("Safety-adjusted", report)

    def test_report_contains_probe_limited_section(self) -> None:
        results = [
            {"domain": "x.com", "classification": "DNS_FAILURE",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "REVIEW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        report = generate_report({"test-mode": br}, "/tmp")
        self.assertIn("Probe-Limited", report)

    def test_report_has_under_blocking_section(self) -> None:
        results = [
            {"domain": "y.com", "classification": "DNS_FAILURE",
             "expected_policy": "AVAILABILITY_RISK", "final_decision": "ALLOW"},
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        report = generate_report({"test-mode": br}, "/tmp")
        self.assertIn("Under-blocking", report)

    def test_over_blocking_shows_limited_rows(self) -> None:
        results = [
            {"domain": f"d{i}.com", "classification": "VALID_TLS",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "REVIEW"}
            for i in range(20)
        ]
        br = compute_benchmark_results(results, "test-mode", "test")
        report = generate_report({"test-mode": br}, "/tmp")
        self.assertIn("... and 10 more", report)


class TestOperatingProfiles(unittest.TestCase):
    """Phase 8: Decision operating profile support."""

    VALID_TLS_ARGS = dict(
        adapter_risk_category="ACCEPTABLE_TLS",
        adapter_severity="NONE",
        adapter_action_hint="NONE",
        classification="VALID_TLS",
        spl_decision=False,
        spl_confidence=0.0,
    )

    SECURITY_RISK_ARGS = dict(
        adapter_risk_category="SECURITY_RISK",
        adapter_severity="HIGH",
        adapter_action_hint="IMMEDIATE_REVIEW",
        classification="EXPIRED_CERT",
        spl_decision=None,
        spl_confidence=0.0,
    )

    def test_conservative_profile_is_accepted(self) -> None:
        out = decide(**self.VALID_TLS_ARGS, profile="conservative")
        self.assertEqual(out["final_decision"], "REVIEW")

    def test_balanced_profile_is_accepted(self) -> None:
        out = decide(**self.VALID_TLS_ARGS, profile="balanced")
        self.assertEqual(out["final_decision"], "REVIEW")

    def test_strict_profile_is_accepted(self) -> None:
        out = decide(**self.VALID_TLS_ARGS, profile="strict")
        self.assertEqual(out["final_decision"], "REVIEW")

    def test_invalid_profile_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            decide(**self.VALID_TLS_ARGS, profile="invalid_profile")

    def test_invalid_profile_raises_value_error_none(self) -> None:
        with self.assertRaises(ValueError):
            decide(**self.VALID_TLS_ARGS, profile=None)  # type: ignore[arg-type]

    def test_invalid_profile_raises_value_error_empty(self) -> None:
        with self.assertRaises(ValueError):
            decide(**self.VALID_TLS_ARGS, profile="")

    def test_conservative_has_07_threshold(self) -> None:
        args = dict(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
        )
        out = decide(**args, spl_confidence=0.6, profile="conservative")
        self.assertEqual(out["final_decision"], "REVIEW")
        out2 = decide(**args, spl_confidence=0.8, profile="conservative")
        self.assertEqual(out2["final_decision"], "ALLOW")

    def test_balanced_has_05_threshold(self) -> None:
        args = dict(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
        )
        out = decide(**args, spl_confidence=0.4, profile="balanced")
        self.assertEqual(out["final_decision"], "REVIEW")
        out2 = decide(**args, spl_confidence=0.6, profile="balanced")
        self.assertEqual(out2["final_decision"], "ALLOW")

    def test_strict_has_07_threshold(self) -> None:
        args = dict(
            adapter_risk_category="ACCEPTABLE_TLS",
            adapter_severity="NONE",
            adapter_action_hint="NONE",
            classification="VALID_TLS",
            spl_decision=False,
        )
        out = decide(**args, spl_confidence=0.6, profile="strict")
        self.assertEqual(out["final_decision"], "REVIEW")
        out2 = decide(**args, spl_confidence=0.8, profile="strict")
        self.assertEqual(out2["final_decision"], "ALLOW")

    def test_conservative_reviews_high_security_risk(self) -> None:
        out = decide(**self.SECURITY_RISK_ARGS, profile="conservative")
        self.assertEqual(out["final_decision"], "REVIEW")

    def test_balanced_reviews_high_security_risk(self) -> None:
        out = decide(**self.SECURITY_RISK_ARGS, profile="balanced")
        self.assertEqual(out["final_decision"], "REVIEW")

    def test_strict_denies_high_security_risk(self) -> None:
        out = decide(**self.SECURITY_RISK_ARGS, profile="strict")
        self.assertEqual(out["final_decision"], "DENY")

    def test_strict_denies_critical_all_profiles(self) -> None:
        critical_args = dict(
            adapter_risk_category="SECURITY_RISK",
            adapter_severity="CRITICAL",
            adapter_action_hint="IMMEDIATE_REVIEW",
            classification="EXPIRED_CERT",
            spl_decision=None,
            spl_confidence=0.0,
        )
        for p in ("conservative", "balanced", "strict"):
            out = decide(**critical_args, profile=p)
            self.assertEqual(out["final_decision"], "DENY")

    def test_profile_includes_name_in_reasons(self) -> None:
        for p in ("conservative", "balanced", "strict"):
            out = decide(**self.VALID_TLS_ARGS, profile=p)
            self.assertIn(f"Profile: {p}", out["supporting_reasons"])

    def test_ofe_metadata_never_affects_decisions_across_profiles(self) -> None:
        no_ofe: OrchestratorOutput = decide(**self.VALID_TLS_ARGS, profile="conservative")
        ofe_sigs: OrchestratorOutput = decide(
            **self.VALID_TLS_ARGS, profile="conservative",
            ofe_signals={"anomaly_score": 0.8},
        )
        self.assertEqual(no_ofe["final_decision"], ofe_sigs["final_decision"])

        no_ofe_b = decide(**self.VALID_TLS_ARGS, profile="balanced")
        ofe_sigs_b = decide(
            **self.VALID_TLS_ARGS, profile="balanced",
            ofe_signals={"anomaly_score": 0.8},
        )
        self.assertEqual(no_ofe_b["final_decision"], ofe_sigs_b["final_decision"])

        no_ofe_s = decide(**self.VALID_TLS_ARGS, profile="strict")
        ofe_sigs_s = decide(
            **self.VALID_TLS_ARGS, profile="strict",
            ofe_signals={"anomaly_score": 0.8},
        )
        self.assertEqual(no_ofe_s["final_decision"], ofe_sigs_s["final_decision"])

    def test_profile_benchmark_results_include_decision_distribution(self) -> None:
        results = [
            {"domain": "a.com", "classification": "VALID_TLS",
             "expected_policy": "ACCEPTABLE_TLS", "final_decision": "ALLOW",
             "is_exact_match": True, "is_safe_mismatch": False,
             "is_unsafe_mismatch": False, "is_over_blocking": False},
            {"domain": "b.com", "classification": "EXPIRED_CERT",
             "expected_policy": "SECURITY_RISK", "final_decision": "DENY",
             "is_exact_match": True, "is_safe_mismatch": False,
             "is_unsafe_mismatch": False, "is_over_blocking": False},
        ]
        br = compute_benchmark_results(results, "test-profile-mode", "test")
        dd = br["decision_distribution"]
        self.assertEqual(dd["ALLOW"], 1)
        self.assertEqual(dd["DENY"], 1)
        self.assertEqual(dd.get("REVIEW", 0), 0)
        self.assertIn("mode", br)
        self.assertEqual(br["mode"], "test-profile-mode")


if __name__ == "__main__":
    unittest.main()
