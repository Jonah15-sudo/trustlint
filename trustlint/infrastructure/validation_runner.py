"""Offline SPL validation/research utility.

This module provides an offline validation pipeline for TLS probe evidence.
It is NOT intended for production ALLOW/DENY decisions. It performs no
network I/O and uses only in-memory message passing.

See docs/SPL_VALIDATION_FINDINGS.md for SPL research limitations.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Set
from spl_v7.dsl import FeatureDSLProgram
from spl_v7.kafka_pipeline import EvidencePipeline, MemoryKafkaAdapter, PipelineConfig
from spl_v7.schema import EvidenceArtifact, EvidenceTransportMeta
from spl_v7.verification import compute_artifact_hash
from tls_policy_adapter.classifications import (
    DEPRECATED_TLS_CLASSIFICATION,
    DEPRECATED_TLS_VERSIONS,
)

__all__ = [
    "CLASSIFICATION_TO_POLICY",
    "CLASSIFICATION_IS_SECURITY",
    "CLASSIFICATION_IS_AVAILABILITY",
    "CLASSIFICATION_IS_AMBIGUOUS",
    "POLICY_LABELS",
    "DEPRECATED_TLS_CLASSIFICATION",
    "REPORT_DIR",
    "_resolve_classification",
    "_decision_to_risk_label",
    "_probe_result_to_evidence",
    "_compute_policy_conformance",
    "_load_decision_expectations",
    "_load_train_expectations",
    "_make_pipeline",
    "_run_pipeline_eval",
    "_train_pipeline",
    "_train_pipeline_with_labels",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPORT_DIR = os.path.join(PROJECT_ROOT, "reports", "local_real_validation")

POLICY_LABELS: Set[str] = {
    "ACCEPTABLE_TLS",
    "SECURITY_RISK",
    "AVAILABILITY_RISK",
    "AMBIGUOUS_FAILURE",
}

CLASSIFICATION_TO_POLICY: Dict[str, str] = {
    "VALID_TLS": "ACCEPTABLE_TLS",
    "DEPRECATED_TLS_VERSION": "SECURITY_RISK",
    "EXPIRED_CERT": "SECURITY_RISK",
    "SELF_SIGNED_CERT": "SECURITY_RISK",
    "WRONG_HOST_CERT": "SECURITY_RISK",
    "UNTRUSTED_CHAIN": "SECURITY_RISK",
    "INCOMPLETE_CHAIN": "SECURITY_RISK",
    "WEAK_SIGNATURE_ALGORITHM": "SECURITY_RISK",
    "REVOKED_CERT": "SECURITY_RISK",
    "WEAK_CIPHER_SUITE": "SECURITY_RISK",
    "STATIC_RSA_KEY_EXCHANGE": "SECURITY_RISK",
    "TLS_COMPRESSION_ENABLED": "SECURITY_RISK",
    "DNS_FAILURE": "AVAILABILITY_RISK",
    "CONNECTION_ERROR": "AVAILABILITY_RISK",
    "TIMEOUT": "AVAILABILITY_RISK",
    "OCSP_UNREACHABLE": "AVAILABILITY_RISK",
    "TLS_HANDSHAKE_FAILURE": "AMBIGUOUS_FAILURE",
    "UNKNOWN_SSL_ERROR": "AMBIGUOUS_FAILURE",
    "WILDCARD_CERTIFICATE": "ACCEPTABLE_TLS",
    "MISSING_OCSP_STAPLE": "ACCEPTABLE_TLS",
}

CLASSIFICATION_IS_SECURITY: Set[str] = {
    "DEPRECATED_TLS_VERSION",
    "EXPIRED_CERT",
    "SELF_SIGNED_CERT",
    "WRONG_HOST_CERT",
    "UNTRUSTED_CHAIN",
    "INCOMPLETE_CHAIN",
    "WEAK_SIGNATURE_ALGORITHM",
    "REVOKED_CERT",
    "WEAK_CIPHER_SUITE",
    "STATIC_RSA_KEY_EXCHANGE",
    "TLS_COMPRESSION_ENABLED",
}

CLASSIFICATION_IS_AVAILABILITY: Set[str] = {
    "DNS_FAILURE",
    "CONNECTION_ERROR",
    "TIMEOUT",
    "OCSP_UNREACHABLE",
}

CLASSIFICATION_IS_AMBIGUOUS: Set[str] = {
    "TLS_HANDSHAKE_FAILURE",
    "UNKNOWN_SSL_ERROR",
}

# DSL for the causal learner (transport-status features only).
# No ternary expressions (IfExp is rejected by the parser).
_DEFAULT_DSL_TEXT = (
    "feature http_error_flag = normalize(transport_meta.status == 'error')\n"
    "feature partial_flag = normalize(transport_meta.status == 'partial')\n"
    "feature timeout_flag = normalize(transport_meta.status == 'timeout')\n"
)


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------


def _resolve_classification(probe_result: Dict[str, Any]) -> str:
    """Reclassify VALID_TLS to DEPRECATED_TLS_VERSION when TLS version is deprecated.

    Does not overwrite existing non-VALID_TLS classifications.
    """
    classification = probe_result.get("classification", "")
    if classification != "VALID_TLS":
        return classification

    tls_info = probe_result.get("tls")
    if tls_info is None:
        return classification

    tls_version = tls_info.get("tls_version")
    if tls_version is None:
        return classification

    if tls_version.lower() in DEPRECATED_TLS_VERSIONS:
        return DEPRECATED_TLS_CLASSIFICATION

    return classification


def _decision_to_risk_label(
    decision: bool,
    probability: float,
    classification: str,
) -> str:
    """Map a decision, probability, and classification to a risk label.

    Rules:
    - decision=False always returns ACCEPTABLE_TLS.
    - known classifications use CLASSIFICATION_TO_POLICY.
    - unknown classifications use probability thresholds:
        >= 0.60 -> SECURITY_RISK
        > 0.30 and < 0.60 -> AMBIGUOUS_FAILURE
        <= 0.30 -> AVAILABILITY_RISK
    """
    if not decision:
        return "ACCEPTABLE_TLS"

    policy = CLASSIFICATION_TO_POLICY.get(classification)
    if policy is not None:
        return policy

    # Unknown classification: use probability thresholds
    if probability >= 0.60:
        return "SECURITY_RISK"
    if probability > 0.30:
        return "AMBIGUOUS_FAILURE"
    return "AVAILABILITY_RISK"


# ---------------------------------------------------------------------------
# Evidence construction
# ---------------------------------------------------------------------------

_STATUS_MAP = {
    "TIMEOUT": "timeout",
}


def _classification_to_transport_status(
    classification: str,
    overall_status: str,
) -> str:
    """Map classification and overall_status to transport_meta.status."""
    if overall_status == "valid":
        return "ok"
    return _STATUS_MAP.get(classification, "error")


def _probe_result_to_evidence(
    probe_result: Dict[str, Any],
    classification: str,
    include_label: bool = False,
) -> EvidenceArtifact:
    """Construct an EvidenceArtifact from a probe result.

    Sets integrity.hash, tags, transport_meta, and data fields.
    The include_label parameter controls whether data["label"] is added.
    """
    domain = probe_result.get("domain", "unknown")
    overall_status = probe_result.get("overall_status", "error")
    transport_status = _classification_to_transport_status(
        classification, overall_status
    )

    # Build data dict
    valid = classification == "VALID_TLS"
    data: Dict[str, Any] = {"valid": valid}
    if include_label:
        data["label"] = not valid

    # Build transport meta
    transport_meta = EvidenceTransportMeta(status=transport_status)

    # Build artifact
    artifact = EvidenceArtifact(
        source="real-tls-probe",
        type="tls_probe",
        data=data,
        transport_meta=transport_meta,
        tags=[classification, "real-tls-probe", domain],
    )
    artifact.integrity.hash = compute_artifact_hash(artifact)
    return artifact


# ---------------------------------------------------------------------------
# Weakness flags
# ---------------------------------------------------------------------------


def _compute_weakness_flags(probe_result: Dict[str, Any]) -> Dict[str, float]:
    """Compute weakness flags from a probe result.

    Rules:
    - http_error_flag: 1.0 only for transport status "error"
    - partial_flag: 1.0 only for transport status "partial"
    - timeout_flag: 1.0 only for transport status "timeout"
    - hsts_missing: 1.0 only when explicit header evidence shows HSTS absent
    - surface_tension: min(1.0, sum of adverse flags)
    """
    classification = probe_result.get("classification", "")
    overall_status = probe_result.get("overall_status", "unknown")
    transport_status = _classification_to_transport_status(
        classification, overall_status
    )

    http_error_flag = 1.0 if transport_status == "error" else 0.0
    partial_flag = 1.0 if transport_status == "partial" else 0.0
    timeout_flag = 1.0 if transport_status == "timeout" else 0.0

    # hsts_missing: only if explicit header evidence exists
    headers = probe_result.get("headers")
    if headers is not None and "strict-transport-security" in headers:
        hsts_value = headers["strict-transport-security"]
        hsts_missing = 0.0 if hsts_value is not None else 1.0
    else:
        hsts_missing = 0.0

    surface_tension = min(
        1.0, http_error_flag + partial_flag + timeout_flag + hsts_missing
    )

    return {
        "http_error_flag": http_error_flag,
        "partial_flag": partial_flag,
        "hsts_missing": hsts_missing,
        "timeout_flag": timeout_flag,
        "surface_tension": surface_tension,
    }


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _make_pipeline() -> EvidencePipeline:
    """Construct an in-memory EvidencePipeline with default DSL."""
    dsl = FeatureDSLProgram.from_text(_DEFAULT_DSL_TEXT)
    config = PipelineConfig(backend="memory")
    adapter = MemoryKafkaAdapter()
    return EvidencePipeline(feature_program=dsl, config=config, adapter=adapter)


def _run_pipeline_eval(
    pipeline: EvidencePipeline,
    probe_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Evaluate probe results through the pipeline.

    Returns a list of result dicts, each containing:
    domain, classification, spl_decision, spl_probability, spl_risk_label,
    weakness_flags, policy_from_classification.
    """
    results: List[Dict[str, Any]] = []

    for pr in probe_results:
        classification = _resolve_classification(pr)
        domain = pr.get("domain", "unknown")

        # Create evidence artifact (no label for evaluation)
        artifact = _probe_result_to_evidence(pr, classification, include_label=False)

        # Ingest and process
        pipeline.ingest(artifact.to_dict())
        pipeline_output = pipeline.process_one(timeout=0.5)

        # Extract pipeline results
        if pipeline_output is not None:
            probability = pipeline_output.get("causal_probability", 0.5)
            decision = pipeline_output.get("decision", False)
        else:
            probability = 0.5
            decision = False

        risk_label = _decision_to_risk_label(decision, probability, classification)
        weakness_flags = _compute_weakness_flags(pr)
        policy = CLASSIFICATION_TO_POLICY.get(classification, "UNKNOWN_RISK")

        results.append(
            {
                "domain": domain,
                "classification": classification,
                "spl_decision": decision,
                "spl_probability": probability,
                "spl_risk_label": risk_label,
                "weakness_flags": weakness_flags,
                "policy_from_classification": policy,
            }
        )

    return results


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def _train_pipeline(
    pipeline: EvidencePipeline,
    probe_results: List[Dict[str, Any]],
) -> None:
    """Train the pipeline using proxy labels derived from classification."""
    for pr in probe_results:
        classification = _resolve_classification(pr)
        artifact = _probe_result_to_evidence(
            pr, classification, include_label=True
        )
        pipeline.ingest(artifact.to_dict())
        pipeline.process_one(timeout=0.5)


def _train_pipeline_with_labels(
    pipeline: EvidencePipeline,
    probe_results: List[Dict[str, Any]],
    labels: Dict[str, bool],
) -> None:
    """Train the pipeline with external clean/dirty labels.

    Missing domains fall back to proxy labels.
    """
    for pr in probe_results:
        classification = _resolve_classification(pr)
        domain = pr.get("domain", "unknown")

        # Use external label if available, otherwise proxy
        if domain in labels:
            artifact = _probe_result_to_evidence(
                pr, classification, include_label=True
            )
            # Override data["label"] with external label
            artifact.data["label"] = labels[domain]
            artifact.integrity.hash = compute_artifact_hash(artifact)
        else:
            artifact = _probe_result_to_evidence(
                pr, classification, include_label=True
            )

        pipeline.ingest(artifact.to_dict())
        pipeline.process_one(timeout=0.5)


# ---------------------------------------------------------------------------
# Expectations loading
# ---------------------------------------------------------------------------


def _load_decision_expectations(path: str) -> Dict[str, str]:
    """Load decision expectations from a JSON file.

    Expected format: {"decisions": [{"domain": ..., "expected_decision": ...}]}
    Returns dict mapping domain -> expected_decision.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    expectations: Dict[str, str] = {}
    for entry in data.get("decisions", []):
        expectations[entry["domain"]] = entry["expected_decision"]
    return expectations


def _load_train_expectations(path: str) -> Dict[str, bool]:
    """Load training expectations from a JSON file.

    Expected format: {"labels": [{"domain": ..., "label": ...}]}
    Returns dict mapping domain -> label (True=problematic, False=clean).
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    labels: Dict[str, bool] = {}
    for entry in data.get("labels", []):
        labels[entry["domain"]] = entry["label"]
    return labels


# ---------------------------------------------------------------------------
# Conformance scoring
# ---------------------------------------------------------------------------


def _compute_policy_conformance(
    results: List[Dict[str, Any]],
    expectations: Dict[str, str],
) -> Dict[str, Any]:
    """Compute conformance between results and expectations.

    Returns dict with total_with_results, correct, conformance_pct, mismatches.
    Does not modify inputs.
    """
    total = len(results)
    correct = 0
    mismatches: List[Dict[str, Any]] = []

    for r in results:
        domain = r.get("domain", "")
        predicted = r.get("spl_risk_label", "")
        expected = expectations.get(domain)

        if expected is not None and predicted == expected:
            correct += 1
        elif expected is not None:
            mismatches.append(
                {
                    "domain": domain,
                    "predicted": predicted,
                    "expected": expected,
                }
            )

    conformance_pct = (correct / total * 100.0) if total > 0 else 0.0

    return {
        "total_with_results": total,
        "correct": correct,
        "conformance_pct": conformance_pct,
        "mismatches": mismatches,
    }
