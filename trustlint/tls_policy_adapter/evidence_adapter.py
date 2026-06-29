"""Evidence enrichment layer for the TLS Risk Policy Adapter.

Produces enriched evidence fields that can be injected into SPL evidence
artifacts or used independently for benchmark comparison.

The enrichment is deterministic — it reads only the probe classification
and metadata, never expectations or labels.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict

from tls_policy_adapter.risk_policy import classify_risk
from tls_policy_adapter.schema import TLSPolicyEvidence


class EnrichedEvidence(TypedDict, total=False):
    """Structured enriched evidence fields produced by the adapter.

    These fields are designed to be injected into an SPL EvidenceArtifact
    without modifying SPL Core or changing SPL decision logic.
    """

    tls_policy_risk: str
    tls_risk_severity: str
    tls_failure_family: str
    tls_policy_reason: str
    tls_action_hint: str


class AdapterBenchmarkResult(TypedDict, total=False):
    """Per-domain benchmark comparison between adapter and expectations.

    The adapter produces risk evidence. The benchmark compares that evidence
    against the policy decision expected for the domain.
    """

    domain: str
    classification: str
    expected_policy: str
    adapter_risk_category: str
    adapter_severity: str
    adapter_action_hint: str
    adapter_conformant: bool
    spl_decision: Optional[bool]
    spl_policy_label: Optional[str]
    spl_conformant: Optional[bool]


def enrich_evidence(classification: str) -> EnrichedEvidence:
    """Produce enriched evidence dict from a TLS classification string.

    Args:
        classification: A TLS classification string (e.g. "EXPIRED_CERT").

    Returns:
        EnrichedEvidence dict with deterministic risk fields.
    """
    evidence: TLSPolicyEvidence = classify_risk(classification)
    return EnrichedEvidence(
        tls_policy_risk=evidence.risk_category,
        tls_risk_severity=evidence.severity,
        tls_failure_family=evidence.failure_family,
        tls_policy_reason=evidence.policy_reason,
        tls_action_hint=evidence.action_hint,
    )


def enrich_evidence_artifact(
    classification: str,
    evidence_artifact: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Produce enriched evidence and optionally merge into an existing artifact.

    Args:
        classification: A TLS classification string.
        evidence_artifact: Optional SPL EvidenceArtifact dict to merge into.
                           If provided, the enriched fields are added under
                           a "tls_policy" key. The original artifact is not
                           modified (a new dict is returned).

    Returns:
        Dict with enriched evidence. If evidence_artifact was provided,
        the result is a shallow copy with "tls_policy" added.
    """
    enriched: EnrichedEvidence = enrich_evidence(classification)

    if evidence_artifact is not None:
        result: Dict[str, Any] = dict(evidence_artifact)
        result["tls_policy"] = dict(enriched)
        return result

    return dict(enriched)
