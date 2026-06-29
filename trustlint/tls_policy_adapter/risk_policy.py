"""Deterministic risk classification logic for TLS probe results.

Provides the core mapping functions that turn a TLS classification string
into a structured TLSPolicyEvidence object. No learning, no expectations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from tls_policy_adapter.schema import (
    RISK_MAP,
    SEVERITY_ORDER,
    TLSClassification,
    TLSFailureFamily,
    TLSPolicyEvidence,
    TLSRiskCategory,
    TLSSeverity,
)


SEVERITY_RANK: Dict[TLSSeverity, int] = {
    sev: idx for idx, sev in enumerate(SEVERITY_ORDER)
}


def classify_risk(classification: str) -> TLSPolicyEvidence:
    """Map a TLS classification string to structured risk evidence.

    Args:
        classification: A TLS classification string (e.g. "EXPIRED_CERT").

    Returns:
        TLSPolicyEvidence with deterministic risk fields.

    Raises:
        KeyError: If the classification is not recognized.
    """
    if classification not in RISK_MAP:
        raise KeyError(
            f"Unknown TLS classification: '{classification}'. "
            f"Recognized: {', '.join(sorted(RISK_MAP.keys()))}"
        )
    return RISK_MAP[classification]


def classify_risk_from_probe(probe_result: Dict[str, Any]) -> TLSPolicyEvidence:
    """Extract classification from a probe result dict and map to risk evidence.

    Args:
        probe_result: A dict with at least a "classification" key,
                      as produced by scripts.run_local_tls_validation.probe_domain().

    Returns:
        TLSPolicyEvidence with deterministic risk fields.

    Raises:
        KeyError: If classification is missing or unrecognized.
    """
    classification = probe_result.get("classification")
    if not classification:
        raise KeyError(
            "Probe result missing 'classification' field. "
            f"Keys present: {list(probe_result.keys())}"
        )
    return classify_risk(classification)


def is_severity_gte(evidence: TLSPolicyEvidence, threshold: TLSSeverity) -> bool:
    """Check whether the evidence severity is >= a given threshold.

    Uses SEVERITY_ORDER for comparison: NONE < LOW < MEDIUM < HIGH < CRITICAL.
    """
    return SEVERITY_RANK[evidence.severity] >= SEVERITY_RANK[threshold]
