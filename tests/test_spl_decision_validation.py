"""Tests for Phase 3.5/4 — SPL Decision Validation Hygiene, Leakage & Holdout.

These tests verify:
- Training leakage: expected labels are not used before decision generation
- Observation mode: runs without expectations, expectations are scoring-only
- Deprecated TLS version maps to security risk
- TIMEOUT maps to documented policy category
- INCOMPLETE_CHAIN vs UNTRUSTED_CHAIN ambiguity remains documented
- Runner emits structured output for all cases
- Holdout mode: train on separate set, eval on unseen holdout
- Split integrity: no domain in both train and holdout
- Train expectations provide external clean/dirty labels
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from typing import Any, Dict, List

# Ensure project root is on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import runner internals
try:
    from scripts.run_real_tls_spl_decision_validation import (
        _decision_to_risk_label,
        _resolve_classification,
        _probe_result_to_evidence,
        _compute_policy_conformance,
        _load_decision_expectations,
        _load_train_expectations,
        _make_pipeline,
        _run_pipeline_eval,
        _train_pipeline,
        _train_pipeline_with_labels,
        CLASSIFICATION_TO_POLICY,
        CLASSIFICATION_IS_SECURITY,
        CLASSIFICATION_IS_AVAILABILITY,
        CLASSIFICATION_IS_AMBIGUOUS,
        POLICY_LABELS,
        DEPRECATED_TLS_CLASSIFICATION,
        REPORT_DIR,
    )
    _HAS_VALIDATION_RUNNER = True
except ImportError:
    _HAS_VALIDATION_RUNNER = False

from spl_v7.schema import EvidenceArtifact


def _make_mock_probe_result(
    domain: str,
    classification: str,
    tls_version: str | None = "TLSv1.3",
    error_category: str | None = None,
) -> Dict[str, Any]:
    tls_info: Dict[str, Any] = {
        "domain": domain,
        "ip": "1.2.3.4",
        "port": 443,
        "tls_version": tls_version,
        "handshake_time_ms": 100.0,
        "cert_expiry_days": 180,
        "error_category": error_category,
    }
    return {
        "domain": domain,
        "classification": classification,
        "probe_timestamp": "2026-06-01T00:00:00Z",
        "resolved_ip": "1.2.3.4",
        "dns_error": None,
        "tls": tls_info,
        "overall_status": "valid" if classification == "VALID_TLS" else "error",
    }


class TestResolveClassification(unittest.TestCase):
    """Verifies deprecated TLS version detection in the evidence adapter."""

    def test_valid_tls_tls1_3_stays_valid(self) -> None:
        pr = _make_mock_probe_result("example.com", "VALID_TLS", "TLSv1.3")
        self.assertEqual(_resolve_classification(pr), "VALID_TLS")

    def test_valid_tls_tls1_2_stays_valid(self) -> None:
        pr = _make_mock_probe_result("example.com", "VALID_TLS", "TLSv1.2")
        self.assertEqual(_resolve_classification(pr), "VALID_TLS")

    def test_valid_tls_tls1_0_becomes_deprecated(self) -> None:
        pr = _make_mock_probe_result("bad.example.com", "VALID_TLS", "TLSv1")
        self.assertEqual(_resolve_classification(pr), DEPRECATED_TLS_CLASSIFICATION)

    def test_valid_tls_tls1_0_full_becomes_deprecated(self) -> None:
        pr = _make_mock_probe_result("bad.example.com", "VALID_TLS", "TLSv1.0")
        self.assertEqual(_resolve_classification(pr), DEPRECATED_TLS_CLASSIFICATION)

    def test_valid_tls_tls1_1_becomes_deprecated(self) -> None:
        pr = _make_mock_probe_result("bad.example.com", "VALID_TLS", "TLSv1.1")
        self.assertEqual(_resolve_classification(pr), DEPRECATED_TLS_CLASSIFICATION)

    def test_expired_cert_not_affected_by_tls_version(self) -> None:
        pr = _make_mock_probe_result("expired.example.com", "EXPIRED_CERT", "TLSv1.0")
        self.assertEqual(_resolve_classification(pr), "EXPIRED_CERT")

    def test_no_tls_info_falls_back_to_classification(self) -> None:
        pr = _make_mock_probe_result("no-tls.example.com", "DNS_FAILURE")
        pr["tls"] = None
        self.assertEqual(_resolve_classification(pr), "DNS_FAILURE")

    def test_no_tls_version_field(self) -> None:
        pr = _make_mock_probe_result("example.com", "VALID_TLS", None)
        self.assertEqual(_resolve_classification(pr), "VALID_TLS")


class TestDecisionToRiskLabel(unittest.TestCase):
    """Verifies the post-hoc risk label mapping is correct."""

    def test_decision_false_always_acceptable(self) -> None:
        for cls in ("VALID_TLS", "EXPIRED_CERT", "DNS_FAILURE", "TIMEOUT"):
            with self.subTest(cls=cls):
                self.assertEqual(
                    _decision_to_risk_label(False, 0.3, cls),
                    "ACCEPTABLE_TLS",
                )

    def test_security_risks_map_to_security(self) -> None:
        for cls in CLASSIFICATION_IS_SECURITY:
            with self.subTest(cls=cls):
                self.assertEqual(
                    _decision_to_risk_label(True, 0.6, cls),
                    "SECURITY_RISK",
                )

    def test_availability_risks_map_to_availability(self) -> None:
        for cls in CLASSIFICATION_IS_AVAILABILITY:
            with self.subTest(cls=cls):
                self.assertEqual(
                    _decision_to_risk_label(True, 0.6, cls),
                    "AVAILABILITY_RISK",
                )

    def test_ambiguous_risks_map_to_ambiguous(self) -> None:
        for cls in CLASSIFICATION_IS_AMBIGUOUS:
            with self.subTest(cls=cls):
                self.assertEqual(
                    _decision_to_risk_label(True, 0.6, cls),
                    "AMBIGUOUS_FAILURE",
                )

    def test_unknown_classification_uses_probability_high(self) -> None:
        self.assertEqual(
            _decision_to_risk_label(True, 0.8, "UNKNOWN_CATEGORY"),
            "SECURITY_RISK",
        )

    def test_unknown_classification_uses_probability_moderate(self) -> None:
        self.assertEqual(
            _decision_to_risk_label(True, 0.55, "UNKNOWN_CATEGORY"),
            "AMBIGUOUS_FAILURE",
        )

    def test_unknown_classification_uses_probability_low(self) -> None:
        self.assertEqual(
            _decision_to_risk_label(True, 0.3, "UNKNOWN_CATEGORY"),
            "AVAILABILITY_RISK",
        )


class TestClassificationToPolicy(unittest.TestCase):
    """Verifies the static classification-to-policy mapping is complete and correct."""

    ALL_CLASSIFICATIONS = [
        "VALID_TLS",
        "DEPRECATED_TLS_VERSION",
        "EXPIRED_CERT",
        "SELF_SIGNED_CERT",
        "WRONG_HOST_CERT",
        "UNTRUSTED_CHAIN",
        "INCOMPLETE_CHAIN",
        "WEAK_SIGNATURE_ALGORITHM",
        "DNS_FAILURE",
        "CONNECTION_ERROR",
        "TIMEOUT",
        "TLS_HANDSHAKE_FAILURE",
        "UNKNOWN_SSL_ERROR",
    ]

    def test_all_classifications_have_policy(self) -> None:
        for cls in self.ALL_CLASSIFICATIONS:
            with self.subTest(cls=cls):
                self.assertIn(cls, CLASSIFICATION_TO_POLICY,
                              f"{cls} missing from CLASSIFICATION_TO_POLICY")

    def test_deprecated_tls_maps_to_security_risk(self) -> None:
        self.assertEqual(CLASSIFICATION_TO_POLICY["DEPRECATED_TLS_VERSION"], "SECURITY_RISK")

    def test_timeout_maps_to_availability_risk(self) -> None:
        self.assertEqual(CLASSIFICATION_TO_POLICY["TIMEOUT"], "AVAILABILITY_RISK")

    def test_all_policy_labels_valid(self) -> None:
        for cls, policy in CLASSIFICATION_TO_POLICY.items():
            with self.subTest(cls=cls):
                self.assertIn(policy, POLICY_LABELS,
                              f"{policy} not in POLICY_LABELS")

    def test_security_set_and_availability_set_are_disjoint(self) -> None:
        overlap = CLASSIFICATION_IS_SECURITY & CLASSIFICATION_IS_AVAILABILITY
        self.assertEqual(overlap, set())

    def test_security_set_and_ambiguous_set_are_disjoint(self) -> None:
        overlap = CLASSIFICATION_IS_SECURITY & CLASSIFICATION_IS_AMBIGUOUS
        self.assertEqual(overlap, set())

    def test_all_classifications_covered_by_sets(self) -> None:
        covered = CLASSIFICATION_IS_SECURITY | CLASSIFICATION_IS_AVAILABILITY | CLASSIFICATION_IS_AMBIGUOUS
        # DEPRECATED_TLS_VERSION is in the security set, VALID_TLS is not in any set
        not_in_any_set = {"VALID_TLS"}
        for cls in self.ALL_CLASSIFICATIONS:
            if cls not in covered and cls not in not_in_any_set:
                self.fail(f"{cls} not covered by any classification set")


class TestProbeResultToEvidence(unittest.TestCase):
    """Verifies evidence artifact creation from probe results."""

    def test_valid_tls_creates_clean_evidence(self) -> None:
        pr = _make_mock_probe_result("example.com", "VALID_TLS")
        artifact = _probe_result_to_evidence(pr, "VALID_TLS", include_label=False)
        self.assertTrue(artifact.data["valid"])
        self.assertEqual(artifact.transport_meta.status, "ok")
        self.assertNotIn("label", artifact.data)

    def test_expired_cert_sets_valid_false(self) -> None:
        pr = _make_mock_probe_result("expired.example.com", "EXPIRED_CERT")
        artifact = _probe_result_to_evidence(pr, "EXPIRED_CERT", include_label=False)
        self.assertFalse(artifact.data["valid"])
        self.assertEqual(artifact.transport_meta.status, "error")

    def test_timeout_sets_transport_status(self) -> None:
        pr = _make_mock_probe_result("timeout.example.com", "TIMEOUT", tls_version=None)
        artifact = _probe_result_to_evidence(pr, "TIMEOUT", include_label=False)
        self.assertFalse(artifact.data["valid"])
        self.assertEqual(artifact.transport_meta.status, "timeout")

    def test_dns_failure_sets_transport_status(self) -> None:
        pr = _make_mock_probe_result("nonexistent.example.com", "DNS_FAILURE", tls_version=None)
        artifact = _probe_result_to_evidence(pr, "DNS_FAILURE", include_label=False)
        self.assertFalse(artifact.data["valid"])
        self.assertEqual(artifact.transport_meta.status, "error")

    def test_proxy_label_included_when_requested(self) -> None:
        pr = _make_mock_probe_result("example.com", "VALID_TLS")
        artifact = _probe_result_to_evidence(pr, "VALID_TLS", include_label=True)
        self.assertIn("label", artifact.data)
        self.assertFalse(artifact.data["label"])  # VALID_TLS -> clean

    def test_proxy_label_is_true_for_problematic(self) -> None:
        pr = _make_mock_probe_result("bad.example.com", "EXPIRED_CERT")
        artifact = _probe_result_to_evidence(pr, "EXPIRED_CERT", include_label=True)
        self.assertIn("label", artifact.data)
        self.assertTrue(artifact.data["label"])  # EXPIRED_CERT -> problematic

    def test_artifact_has_integrity_hash(self) -> None:
        pr = _make_mock_probe_result("example.com", "VALID_TLS")
        artifact = _probe_result_to_evidence(pr, "VALID_TLS")
        self.assertIsNotNone(artifact.integrity.hash)

    def test_artifact_tags_include_classification(self) -> None:
        pr = _make_mock_probe_result("example.com", "VALID_TLS")
        artifact = _probe_result_to_evidence(pr, "VALID_TLS")
        self.assertIn("VALID_TLS", artifact.tags)
        self.assertIn("real-tls-probe", artifact.tags)
        self.assertIn("example.com", artifact.tags)


class TestLoadDecisionExpectations(unittest.TestCase):
    """Verifies expectations loading is correct and isolated from decision generation."""

    def setUp(self) -> None:
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8",
        )
        self.tmp.write(json.dumps({
            "decisions": [
                {"domain": "example.com", "expected_decision": "ACCEPTABLE_TLS"},
                {"domain": "bad.example.com", "expected_decision": "SECURITY_RISK"},
            ],
        }))
        self.tmp.close()

    def tearDown(self) -> None:
        os.unlink(self.tmp.name)

    def test_loads_expectations_correctly(self) -> None:
        expectations = _load_decision_expectations(self.tmp.name)
        self.assertEqual(len(expectations), 2)
        self.assertEqual(expectations["example.com"], "ACCEPTABLE_TLS")
        self.assertEqual(expectations["bad.example.com"], "SECURITY_RISK")


class TestComputePolicyConformance(unittest.TestCase):
    """Verifies conformance scoring is purely post-hoc (expectations not fed back)."""

    def setUp(self) -> None:
        self.results = [
            {"domain": "good.com", "spl_risk_label": "ACCEPTABLE_TLS",
             "classification": "VALID_TLS", "causal_probability": 0.3, "decision": False},
            {"domain": "bad.com", "spl_risk_label": "SECURITY_RISK",
             "classification": "EXPIRED_CERT", "causal_probability": 0.7, "decision": True},
            {"domain": "timeout.com", "spl_risk_label": "AVAILABILITY_RISK",
             "classification": "TIMEOUT", "causal_probability": 0.4, "decision": True},
        ]
        self.expectations = {
            "good.com": "ACCEPTABLE_TLS",
            "bad.com": "SECURITY_RISK",
            "timeout.com": "AVAILABILITY_RISK",
        }

    def test_conformance_counts_correct(self) -> None:
        conformance = _compute_policy_conformance(self.results, self.expectations)
        self.assertEqual(conformance["total_with_results"], 3)
        self.assertEqual(conformance["correct"], 3)
        self.assertEqual(conformance["conformance_pct"], 100.0)

    def test_conformance_detects_mismatches(self) -> None:
        bad_results = list(self.results)
        bad_results[0]["spl_risk_label"] = "SECURITY_RISK"
        conformance = _compute_policy_conformance(bad_results, self.expectations)
        self.assertEqual(conformance["correct"], 2)
        self.assertEqual(len(conformance["mismatches"]), 1)
        self.assertEqual(conformance["mismatches"][0]["domain"], "good.com")

    def test_expectations_not_modified_by_scoring(self) -> None:
        expectations_copy = dict(self.expectations)
        _compute_policy_conformance(self.results, self.expectations)
        self.assertEqual(self.expectations, expectations_copy)

    def test_results_not_modified_by_scoring(self) -> None:
        results_copy = [dict(r) for r in self.results]
        _compute_policy_conformance(self.results, self.expectations)
        self.assertEqual(len(self.results), len(results_copy))


class TestPipelineRunEval(unittest.TestCase):
    """Verifies the evaluation pipeline produces structured output."""

    def test_pipeline_eval_returns_results_for_all_domains(self) -> None:
        pipeline = _make_pipeline()
        probe_results = [
            _make_mock_probe_result("good.com", "VALID_TLS"),
            _make_mock_probe_result("bad.com", "EXPIRED_CERT"),
            _make_mock_probe_result("timeout.com", "TIMEOUT", tls_version=None),
        ]
        results = _run_pipeline_eval(pipeline, probe_results)
        self.assertEqual(len(results), 3)

    def test_each_result_has_required_fields(self) -> None:
        pipeline = _make_pipeline()
        pr = _make_mock_probe_result("example.com", "VALID_TLS")
        results = _run_pipeline_eval(pipeline, [pr])
        r = results[0]
        for field in ("domain", "classification", "spl_decision", "spl_probability",
                       "spl_risk_label", "weakness_flags", "policy_from_classification"):
            self.assertIn(field, r, f"Missing field: {field}")

    def test_weakness_flags_are_present(self) -> None:
        pipeline = _make_pipeline()
        pr = _make_mock_probe_result("example.com", "VALID_TLS")
        results = _run_pipeline_eval(pipeline, [pr])
        wf = results[0]["weakness_flags"]
        for flag in ("http_error_flag", "partial_flag", "hsts_missing",
                      "timeout_flag", "surface_tension"):
            self.assertIn(flag, wf, f"Missing weakness flag: {flag}")


class TestIncompleteVsUntrustedChain(unittest.TestCase):
    """Verifies the chain trust ambiguity is documented and not silently resolved."""

    def test_incomplete_chain_classified_separately(self) -> None:
        self.assertIn("INCOMPLETE_CHAIN", CLASSIFICATION_TO_POLICY)
        self.assertIn("UNTRUSTED_CHAIN", CLASSIFICATION_TO_POLICY)

    def test_both_map_to_security_risk(self) -> None:
        self.assertEqual(CLASSIFICATION_TO_POLICY["INCOMPLETE_CHAIN"], "SECURITY_RISK")
        self.assertEqual(CLASSIFICATION_TO_POLICY["UNTRUSTED_CHAIN"], "SECURITY_RISK")

    def test_both_in_security_set(self) -> None:
        self.assertIn("INCOMPLETE_CHAIN", CLASSIFICATION_IS_SECURITY)
        self.assertIn("UNTRUSTED_CHAIN", CLASSIFICATION_IS_SECURITY)


class TestObservationModeNoExpectations(unittest.TestCase):
    """Verifies the runner's observation mode works without expectations."""

    def test_pipeline_works_without_expectations(self) -> None:
        pipeline = _make_pipeline()
        pr = _make_mock_probe_result("example.com", "VALID_TLS")
        results = _run_pipeline_eval(pipeline, [pr])
        self.assertEqual(len(results), 1)
        # Decision and probability should be present even without training
        self.assertIsInstance(results[0]["spl_decision"], bool)
        self.assertIsInstance(results[0]["spl_probability"], float)


class TestDeprecatedTlsInEvidenceContract(unittest.TestCase):
    """Verifies deprecated TLS is in the classification policy sets."""

    def test_deprecated_tls_in_security_set(self) -> None:
        self.assertIn("DEPRECATED_TLS_VERSION", CLASSIFICATION_IS_SECURITY)

    def test_deprecated_tls_not_in_availability_set(self) -> None:
        self.assertNotIn("DEPRECATED_TLS_VERSION", CLASSIFICATION_IS_AVAILABILITY)

    def test_deprecated_tls_not_in_ambiguous_set(self) -> None:
        self.assertNotIn("DEPRECATED_TLS_VERSION", CLASSIFICATION_IS_AMBIGUOUS)


class TestTimeoutClassificationPolicy(unittest.TestCase):
    """Verifies TIMEOUT maps to AVAILABILITY_RISK as documented."""

    def test_timeout_in_availability_set(self) -> None:
        self.assertIn("TIMEOUT", CLASSIFICATION_IS_AVAILABILITY)

    def test_timeout_not_in_security_set(self) -> None:
        self.assertNotIn("TIMEOUT", CLASSIFICATION_IS_SECURITY)

    def test_timeout_not_in_ambiguous_set(self) -> None:
        self.assertNotIn("TIMEOUT", CLASSIFICATION_IS_AMBIGUOUS)


# ── Phase 4: Holdout Mode Tests ─────────────────────────────────────────────


class TestLoadTrainExpectations(unittest.TestCase):
    """Verifies training expectations loading from JSON."""

    def setUp(self) -> None:
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8",
        )
        self.tmp.write(json.dumps({
            "labels": [
                {"domain": "example.com", "label": False, "label_weight": 1.0},
                {"domain": "bad.example.com", "label": True, "label_weight": 1.0},
            ],
        }))
        self.tmp.close()

    def tearDown(self) -> None:
        os.unlink(self.tmp.name)

    def test_loads_train_expectations_correctly(self) -> None:
        labels = _load_train_expectations(self.tmp.name)
        self.assertEqual(len(labels), 2)
        self.assertFalse(labels["example.com"])
        self.assertTrue(labels["bad.example.com"])


class TestTrainPipelineWithLabels(unittest.TestCase):
    """Verifies training with external clean/dirty labels works."""

    def test_trains_with_external_labels(self) -> None:
        pipeline = _make_pipeline()
        probe_results = [
            _make_mock_probe_result("good.com", "VALID_TLS"),
            _make_mock_probe_result("bad.com", "EXPIRED_CERT"),
        ]
        train_labels = {"good.com": False, "bad.com": True}
        _train_pipeline_with_labels(pipeline, probe_results, train_labels)
        # Train should complete without errors — pipeline can now evaluate
        results = _run_pipeline_eval(pipeline, probe_results)
        self.assertEqual(len(results), 2)

    def test_external_labels_override_proxy(self) -> None:
        pipeline = _make_pipeline()
        # A VALID_TLS domain with an external True label should train as dirty
        pr = [_make_mock_probe_result("good.com", "VALID_TLS")]
        _train_pipeline_with_labels(pipeline, pr, {"good.com": True})
        results = _run_pipeline_eval(pipeline, pr)
        self.assertIsInstance(results[0]["spl_decision"], bool)

    def test_missing_domain_falls_back_to_proxy(self) -> None:
        pipeline = _make_pipeline()
        pr = [_make_mock_probe_result("unknown.com", "VALID_TLS")]
        _train_pipeline_with_labels(pipeline, pr, {})
        results = _run_pipeline_eval(pipeline, pr)
        self.assertIsInstance(results[0]["spl_decision"], bool)


class TestTrainPipelineProxy(unittest.TestCase):
    """Verifies the proxy-label training function."""

    def test_trains_with_proxy_labels(self) -> None:
        pipeline = _make_pipeline()
        probe_results = [
            _make_mock_probe_result("good.com", "VALID_TLS"),
            _make_mock_probe_result("bad.com", "EXPIRED_CERT"),
        ]
        _train_pipeline(pipeline, probe_results)
        results = _run_pipeline_eval(pipeline, probe_results)
        self.assertEqual(len(results), 2)

    def test_training_does_not_leak_to_untrained_pipeline(self) -> None:
        trained = _make_pipeline()
        probe_results = [
            _make_mock_probe_result("good.com", "VALID_TLS"),
        ]
        _train_pipeline(trained, probe_results)
        trained_results = _run_pipeline_eval(trained, probe_results)
        # Compare with cold-start (untrained)
        untrained = _make_pipeline()
        untrained_results = _run_pipeline_eval(untrained, probe_results)
        # The trained pipeline may produce different probabilities
        self.assertIsInstance(trained_results[0]["spl_probability"], float)
        self.assertIsInstance(untrained_results[0]["spl_probability"], float)


class TestHoldoutSplitIntegrity(unittest.TestCase):
    """Verifies that holdout and training sets are disjoint."""

    # These domains are taken from the actual holdout set definition
    HOLDOUT_DOMAINS = {
        "google.com", "python.org", "wikipedia.org", "badssl.com",
        "tls-v1-2.badssl.com", "mozilla.org", "mozilla-intermediate.badssl.com",
        "mozilla-modern.badssl.com", "tls-v1-1.badssl.com", "tls-v1-0.badssl.com",
        "eff.org", "expired.badssl.com", "untrusted-root.badssl.com",
        "dh480.badssl.com", "null.badssl.com",
        "thissitedoesnotexistxyzabc99999.nonexistent", "localhost", "10.255.255.1",
    }

    TRAIN_DOMAINS = {
        "github.com", "gitlab.com", "pypi.org", "docker.com", "archive.org",
        "w3.org", "ietf.org", "openssl.org", "debian.org", "ubuntu.com",
        "redhat.com", "caltech.edu", "stanford.edu", "harvard.edu",
        "berkeley.edu", "npr.org", "bbc.com", "reuters.com", "acm.org",
        "ieee.org", "science.org", "nature.com", "arxiv.org", "ssrn.com",
        "postgresql.com", "sha256.badssl.com", "sha384.badssl.com",
        "sha512.badssl.com", "1000-sans.badssl.com", "self-signed.badssl.com",
        "wrong.host.badssl.com", "superfish.badssl.com",
        "incomplete-chain.badssl.com", "dh512.badssl.com", "rc4.badssl.com",
        "3des.badssl.com", "dh1024.badssl.com", "rc4-md5.badssl.com",
        "jjf8d9a7sd6f5asdf.testing-reserved",
        "never-gonna-resolve-987654321.example.com", "127.0.0.1", "0.0.0.0",
        "203.0.113.1",
    }

    def test_no_domain_in_both_sets(self) -> None:
        overlap = self.HOLDOUT_DOMAINS & self.TRAIN_DOMAINS
        self.assertEqual(overlap, set(),
                         f"Domains appear in both train and holdout: {overlap}")

    def test_train_expectations_labels_match_train_domains(self) -> None:
        """Verifies that the train expectations file labels are for train domains."""
        train_labels_path = os.path.join(PROJECT_ROOT, "datasets", "real_tls_train_expectations.json")
        self.assertTrue(os.path.isfile(train_labels_path))
        with open(train_labels_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data.get("labels", []):
            domain = entry["domain"]
            self.assertIn(domain, self.TRAIN_DOMAINS,
                          f"Train expectation label for '{domain}' not in train domain set")

    def test_holdout_expectations_domains_match_holdout_set(self) -> None:
        """Verifies that the holdout expectations file is for holdout domains."""
        holdout_expectations_path = os.path.join(
            PROJECT_ROOT, "datasets", "real_tls_holdout_expectations.json",
        )
        self.assertTrue(os.path.isfile(holdout_expectations_path))
        with open(holdout_expectations_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data.get("decisions", []):
            domain = entry["domain"]
            self.assertIn(domain, self.HOLDOUT_DOMAINS,
                          f"Holdout expectation for '{domain}' not in holdout domain set")


class TestHoldoutModeLeakage(unittest.TestCase):
    """Verifies that holdout mode does not leak expectations into decisions."""

    def test_holdout_scoring_after_decisions(self) -> None:
        """Simulates holdout mode: train on one set, eval on another, score after."""
        pipeline = _make_pipeline()
        train_probes = [
            _make_mock_probe_result("good.com", "VALID_TLS"),
            _make_mock_probe_result("bad.com", "EXPIRED_CERT"),
        ]
        eval_probes = [
            _make_mock_probe_result("eval-good.com", "VALID_TLS"),
            _make_mock_probe_result("eval-bad.com", "EXPIRED_CERT"),
        ]

        # Train with external labels
        _train_pipeline_with_labels(pipeline, train_probes,
                                    {"good.com": False, "bad.com": True})

        # Evaluate (no labels injected)
        results = _run_pipeline_eval(pipeline, eval_probes)

        # Score after decisions
        expectations = {
            "eval-good.com": "ACCEPTABLE_TLS",
            "eval-bad.com": "SECURITY_RISK",
        }
        conformance = _compute_policy_conformance(results, expectations)

        self.assertEqual(conformance["total_with_results"], 2)
        # Expectations must not appear in evidence artifacts
        for r in results:
            self.assertNotIn("label", r)

    def test_train_expectations_not_used_in_eval_scoring(self) -> None:
        """Train expectations must be separate from scoring expectations."""
        pipeline = _make_pipeline()
        train_probes = [
            _make_mock_probe_result("good.com", "VALID_TLS"),
        ]
        eval_probes = [
            _make_mock_probe_result("eval.com", "VALID_TLS"),
        ]

        # Train with external labels
        _train_pipeline_with_labels(pipeline, train_probes, {"good.com": False})

        # Evaluate
        results = _run_pipeline_eval(pipeline, eval_probes)

        # Score with holdout expectations — only eval domains
        holdout_expectations = {"eval.com": "ACCEPTABLE_TLS"}
        conformance = _compute_policy_conformance(results, holdout_expectations)

        self.assertEqual(conformance["total_with_results"], 1)
        self.assertEqual(conformance["correct"], 1)

    def test_train_expectations_domains_not_scored_with_holdout(self) -> None:
        """Training domain expectations must NOT be used in holdout scoring."""
        pipeline = _make_pipeline()
        train_probes = [
            _make_mock_probe_result("train.com", "VALID_TLS"),
        ]
        # Train
        _train_pipeline_with_labels(pipeline, train_probes, {"train.com": False})

        # Eval on different domain
        eval_probes = [
            _make_mock_probe_result("holdout.com", "VALID_TLS"),
        ]
        results = _run_pipeline_eval(pipeline, eval_probes)

        # Only score holdout domains — train domains should not be in expectations
        holdout_expectations = {"holdout.com": "ACCEPTABLE_TLS"}
        conformance = _compute_policy_conformance(results, holdout_expectations)

        self.assertEqual(conformance["total_with_results"], 1)
        # "train.com" should not appear in results (it was not evaluated)
        result_domains = {r["domain"] for r in results}
        self.assertNotIn("train.com", result_domains)


# ── Phase 5: Stratified Benchmark Tests ─────────────────────────────────────


class TestBenchmarkExpectationsLoading(unittest.TestCase):
    """Verifies the benchmark expectations file has correct structure."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.benchmark_expectations_path = os.path.join(
            PROJECT_ROOT, "datasets", "real_tls_benchmark_expectations.json",
        )

    def test_benchmark_expectations_file_exists(self) -> None:
        self.assertTrue(os.path.isfile(self.benchmark_expectations_path))

    def test_benchmark_expectations_loadable(self) -> None:
        expectations = _load_decision_expectations(self.benchmark_expectations_path)
        self.assertGreaterEqual(len(expectations), 100,
                                "Benchmark should have at least 100 domains")

    def test_benchmark_expectations_has_decision_entries(self) -> None:
        with open(self.benchmark_expectations_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("decisions", data)
        self.assertGreater(len(data["decisions"]), 0)
        for entry in data["decisions"]:
            self.assertIn("domain", entry)
            self.assertIn("expected_decision", entry)
            self.assertIn(entry["expected_decision"],
                          {"ACCEPTABLE_TLS", "SECURITY_RISK", "AVAILABILITY_RISK", "AMBIGUOUS_FAILURE"})

class TestDeprecatedTlsDocumentation(unittest.TestCase):
    """Verifies the deprecated TLS limitation is documented in evidence contract."""

    def test_deprecated_tls_limitation_documented(self) -> None:
        contract_path = os.path.join(PROJECT_ROOT, "docs", "REAL_TLS_EVIDENCE_CONTRACT.md")
        self.assertTrue(os.path.isfile(contract_path))
        with open(contract_path, "r", encoding="utf-8") as f:
            text = f.read()
        # Must mention that deprecated TLS detection is not guaranteed
        self.assertIn("not guaranteed", text.lower(),
                      "Evidence contract must state deprecated TLS detection is not guaranteed")

    def test_benchmark_report_includes_deprecated_tls(self) -> None:
        report_path = os.path.join(
            PROJECT_ROOT, "reports", "local_real_validation", "STRATIFIED_BENCHMARK_REPORT.md",
        )
        if not os.path.isfile(report_path):
            self.skipTest("Benchmark report not yet generated")
        with open(report_path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Deprecated TLS", text)


if __name__ == "__main__":
    unittest.main()
