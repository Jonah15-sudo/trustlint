"""Schema for the Decision Orchestration Policy.

Defines input/output types for the orchestrator that combines adapter
and SPL outputs into a transparent final decision.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional, TypedDict

FinalDecision = Literal["ALLOW", "REVIEW", "DENY"]
FinalRisk = Literal["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
DecisionSource = Literal["ADAPTER", "ADAPTER_FALLBACK", "SPL", "COMBINED", "CONFIDENCE"]


class OrchestratorInput(TypedDict, total=False):
    """All input fields consumed by the orchestrator.

    Adapter and SPL fields must be provided. OFE and weakness are optional.
    """

    domain: str
    classification: str
    adapter_risk_category: str
    adapter_severity: str
    adapter_action_hint: str
    spl_decision: Optional[bool]
    spl_confidence: float
    spl_policy_label: Optional[str]
    weakness_flags: Optional[List[str]]
    ofe_signals: Optional[Dict[str, float]]
    expected_policy: Optional[str]
    probe_limited: bool


class OrchestratorOutput(TypedDict, total=False):
    """The orchestrator's final structured output.

    All fields are populated after orchestration.
    """

    domain: str
    classification: str
    expected_policy: Optional[str]
    final_decision: str
    final_risk: str
    primary_reason: str
    supporting_reasons: List[str]
    decision_source: str
    fallback_used: bool
    confidence_source: str
    is_exact_match: bool
    is_safe_mismatch: bool
    is_unsafe_mismatch: bool
    is_over_blocking: bool
    spl_decision: Optional[bool]
    spl_confidence: float
    spl_policy_label: Optional[str]
    adapter_risk_category: str
    adapter_severity: str
    adapter_action_hint: str
    ofe_observed: bool


SEVERITY_ORDER: List[str] = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

SEVERITY_RANK: Dict[str, int] = {
    sev: idx for idx, sev in enumerate(SEVERITY_ORDER)
}

OperatingProfile = Literal["conservative", "balanced", "strict"]
