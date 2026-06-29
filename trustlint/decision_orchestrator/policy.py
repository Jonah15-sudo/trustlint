"""Core orchestration policy rules.

Combines adapter risk evidence with SPL decision/confidence into a
transparent final decision. Supports configurable operating profiles.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from decision_orchestrator.schema import (
    OrchestratorInput,
    OrchestratorOutput,
    OperatingProfile,
    SEVERITY_RANK,
)

HIGH_SEVERITY_SECURITY_RISKS: List[str] = [
    "EXPIRED_CERT",
    "SELF_SIGNED_CERT",
    "UNTRUSTED_CHAIN",
    "INCOMPLETE_CHAIN",
    "DEPRECATED_TLS_VERSION",
    "WEAK_CIPHER_SUITE",
]

MEDIUM_SEVERITY_SECURITY_RISKS: List[str] = [
    "STATIC_RSA_KEY_EXCHANGE",
    "TLS_COMPRESSION_ENABLED",
]

LOW_SEVERITY_SECURITY_RISKS: List[str] = [
    "WILDCARD_CERTIFICATE",
    "MISSING_OCSP_STAPLE",
]

AVAILABILITY_CLASSIFICATIONS: List[str] = [
    "DNS_FAILURE",
    "CONNECTION_ERROR",
    "TIMEOUT",
]

AMBIGUOUS_CLASSIFICATIONS: List[str] = [
    "TLS_HANDSHAKE_FAILURE",
    "UNKNOWN_SSL_ERROR",
]

DEPRECATED_TLS_CLASSIFICATION: str = "DEPRECATED_TLS_VERSION"


def _severity_rank(severity: str) -> int:
    return SEVERITY_RANK.get(severity, 0)


_PROFILE_ALLOW_THRESHOLDS: Dict[OperatingProfile, float] = {
    "conservative": 0.7,
    "balanced": 0.5,
    "strict": 0.7,
}

_PROFILE_HIGH_SECURITY_ACTION: Dict[OperatingProfile, str] = {
    "conservative": "REVIEW",
    "balanced": "REVIEW",
    "strict": "DENY",
}




def decide(
    adapter_risk_category: str,
    adapter_severity: str,
    adapter_action_hint: str,
    spl_decision: Optional[bool],
    spl_confidence: float,
    classification: str,
    spl_policy_label: Optional[str] = None,
    weakness_flags: Optional[List[str]] = None,
    ofe_signals: Optional[Dict[str, float]] = None,
    profile: OperatingProfile = "balanced",
    probe_limited: bool = False,
) -> OrchestratorOutput:
    """Apply orchestration rules for the given operating profile.

    Rules evaluated in order (first match wins):

    Conservative:
    1. CRITICAL -> DENY
    2. HIGH security risk -> REVIEW
    3. DEPRECATED_TLS -> REVIEW
    4. MEDIUM availability -> REVIEW
    5. AMBIGUOUS -> REVIEW
    6. VALID_TLS + SPL confidence >= 0.7 -> ALLOW
    7. VALID_TLS + low/no SPL confidence -> REVIEW
    8. Fallback -> REVIEW

    Balanced:
    1. CRITICAL -> DENY
    2. HIGH security risk -> REVIEW
    3. DEPRECATED_TLS -> REVIEW
    4. MEDIUM availability -> REVIEW
    5. AMBIGUOUS -> REVIEW
    6. VALID_TLS + SPL confidence >= 0.5 -> ALLOW
    7. VALID_TLS + no SPL confidence, clean adapter, not probe-limited -> ALLOW (ADAPTER_FALLBACK)
    8. VALID_TLS + low SPL confidence -> REVIEW
    9. Fallback -> REVIEW

    Strict:
    1. CRITICAL -> DENY
    2. HIGH security risk -> DENY
    3. DEPRECATED_TLS -> DENY
    4. MEDIUM availability -> REVIEW
    5. AMBIGUOUS -> REVIEW
    6. VALID_TLS + SPL confidence >= 0.7 -> ALLOW
    7. VALID_TLS + low/no SPL confidence -> REVIEW
    8. Fallback -> REVIEW

    Fallback ALLOW (balanced Rule 7) is a deterministic adapter-based
    local CLI policy, not SPL confidence. It applies only when ALL of:
    - profile is balanced
    - spl_decision is None (no SPL available)
    - classification is VALID_TLS
    - adapter_risk_category is ACCEPTABLE_TLS
    - adapter_severity is NONE
    - probe is NOT limited (no DNS failure, timeout, etc.)
    """
    valid_profiles = ("conservative", "balanced", "strict")
    if profile not in valid_profiles:
        raise ValueError(f"Unknown operating profile: {profile!r}. Valid: {valid_profiles}")

    allow_threshold = _PROFILE_ALLOW_THRESHOLDS[profile]
    high_security_action = _PROFILE_HIGH_SECURITY_ACTION[profile]

    supporting_reasons: List[str] = []
    final_decision: str
    final_risk: str
    decision_source: str
    primary_reason: str
    fallback_used: bool = False
    confidence_source: str = "SPL"

    ofe_observed = (ofe_signals is not None and len(ofe_signals) > 0)

    supporting_reasons.append(f"Profile: {profile}")

    # Rule 1: CRITICAL -> DENY (all profiles)
    if adapter_severity == "CRITICAL":
        final_decision = "DENY"
        final_risk = "CRITICAL"
        decision_source = "ADAPTER"
        primary_reason = f"Adapter severity CRITICAL for {classification}. {adapter_action_hint}"
        supporting_reasons.append(f"Adapter risk: {adapter_risk_category}")
        if spl_decision is not None:
            supporting_reasons.append(f"SPL decision: {'DENY' if spl_decision else 'ALLOW'} (confidence: {spl_confidence:.2f})")
        if spl_decision is None:
            confidence_source = "UNAVAILABLE"

    # Rule 2: HIGH severity security risk -> profile-dependent
    elif classification in HIGH_SEVERITY_SECURITY_RISKS and adapter_severity == "HIGH":
        final_decision = high_security_action
        final_risk = "HIGH"
        decision_source = "ADAPTER"
        primary_reason = f"Security risk ({profile} profile): {adapter_action_hint} for {classification}"
        supporting_reasons.append(f"Adapter risk: {adapter_risk_category}")
        if spl_decision is not None:
            supporting_reasons.append(f"SPL decision: {'DENY' if spl_decision else 'ALLOW'} (confidence: {spl_confidence:.2f})")
        if spl_decision is None:
            confidence_source = "UNAVAILABLE"

    # Rule 2a: MEDIUM security risk -> REVIEW (all profiles)
    elif classification in MEDIUM_SEVERITY_SECURITY_RISKS and adapter_severity == "MEDIUM":
        final_decision = "REVIEW"
        final_risk = "MEDIUM"
        decision_source = "ADAPTER"
        primary_reason = f"Medium-severity security risk ({profile} profile): {adapter_action_hint} for {classification}"
        supporting_reasons.append(f"Adapter risk: {adapter_risk_category}")
        if spl_decision is not None:
            supporting_reasons.append(f"SPL decision: {'DENY' if spl_decision else 'ALLOW'} (confidence: {spl_confidence:.2f})")
        if spl_decision is None:
            confidence_source = "UNAVAILABLE"

    # Rule 2b: LOW informational -> ALLOW (balanced/conservative), REVIEW (strict)
    elif classification in LOW_SEVERITY_SECURITY_RISKS and adapter_severity == "LOW":
        if profile == "strict":
            final_decision = "REVIEW"
            final_risk = "LOW"
            decision_source = "ADAPTER"
            primary_reason = f"Informational ({profile} profile): {adapter_action_hint} for {classification}"
            supporting_reasons.append(f"Adapter risk: {adapter_risk_category}")
        else:
            final_decision = "ALLOW"
            final_risk = "NONE"
            decision_source = "ADAPTER"
            primary_reason = f"Informational concern allowed by {profile} profile: {classification}"
            supporting_reasons.append(f"Adapter risk: {adapter_risk_category}")
        if spl_decision is not None:
            supporting_reasons.append(f"SPL decision: {'DENY' if spl_decision else 'ALLOW'} (confidence: {spl_confidence:.2f})")
        if spl_decision is None:
            confidence_source = "UNAVAILABLE"

    # Rule 3: MEDIUM availability -> REVIEW (all profiles)
    elif classification in AVAILABILITY_CLASSIFICATIONS and adapter_severity == "MEDIUM":
        final_decision = "REVIEW"
        final_risk = "MEDIUM"
        decision_source = "ADAPTER"
        primary_reason = f"Availability risk: {adapter_action_hint} for {classification}"
        supporting_reasons.append(f"Adapter risk: {adapter_risk_category}")
        if spl_decision is not None:
            supporting_reasons.append(f"SPL decision: {'DENY' if spl_decision else 'ALLOW'} (confidence: {spl_confidence:.2f})")
        if spl_decision is None:
            confidence_source = "UNAVAILABLE"

    # Rule 4: AMBIGUOUS -> REVIEW (all profiles)
    elif classification in AMBIGUOUS_CLASSIFICATIONS:
        final_decision = "REVIEW"
        final_risk = "MEDIUM" if classification == "TLS_HANDSHAKE_FAILURE" else "LOW"
        decision_source = "ADAPTER"
        primary_reason = f"Ambiguous failure: {adapter_action_hint} for {classification}"
        supporting_reasons.append(f"Adapter risk: {adapter_risk_category}")
        if spl_decision is not None:
            supporting_reasons.append(f"SPL decision: {'DENY' if spl_decision else 'ALLOW'} (confidence: {spl_confidence:.2f})")
        if spl_decision is None:
            confidence_source = "UNAVAILABLE"

    # Rule 5: VALID_TLS + SPL confidence >= threshold -> ALLOW
    elif classification == "VALID_TLS" and spl_decision is not None and spl_confidence >= allow_threshold:
        final_decision = "ALLOW"
        final_risk = "NONE"
        decision_source = "SPL" if spl_decision is False else "COMBINED"
        primary_reason = f"VALID_TLS with SPL confidence {spl_confidence:.2f} (profile: {profile}, threshold: {allow_threshold})"
        supporting_reasons.append("Adapter: ACCEPTABLE_TLS")
        supporting_reasons.append(f"SPL decision: {'DENY' if spl_decision else 'ALLOW'} (confidence: {spl_confidence:.2f})")
        confidence_source = "SPL"

    # Rule 6: VALID_TLS + balanced + no SPL + clean adapter + not probe-limited -> ALLOW (fallback)
    elif classification == "VALID_TLS" and spl_decision is None and profile == "balanced" and adapter_risk_category == "ACCEPTABLE_TLS" and adapter_severity == "NONE" and not probe_limited:
        final_decision = "ALLOW"
        final_risk = "NONE"
        decision_source = "ADAPTER_FALLBACK"
        fallback_used = True
        confidence_source = "FALLBACK"
        primary_reason = f"VALID_TLS allowed by {profile} profile fallback policy because SPL confidence is unavailable and probe result is clean"
        supporting_reasons.append("Adapter: ACCEPTABLE_TLS (NONE severity)")
        supporting_reasons.append("SPL confidence: unavailable (adapter-only mode)")
        supporting_reasons.append("Fallback ALLOW is a deterministic adapter-based CLI policy, not SPL confidence")
        supporting_reasons.append("This ALLOW does not indicate production readiness")

    # Rule 7: VALID_TLS + SPL low confidence or no fallback conditions -> REVIEW
    elif classification == "VALID_TLS":
        if spl_decision is None:
            final_decision = "REVIEW"
            final_risk = "LOW"
            decision_source = "CONFIDENCE"
            primary_reason = f"VALID_TLS but SPL confidence is unavailable ({profile} profile: {'fallback conditions not met' if profile != 'balanced' else 'probe limited or adapter not clean'})"
            supporting_reasons.append("Adapter: ACCEPTABLE_TLS")
            supporting_reasons.append("SPL confidence: unavailable (adapter-only mode)")
            confidence_source = "UNAVAILABLE"
            if probe_limited:
                supporting_reasons.append("Probe result is limited — cannot safely fallback to ALLOW")
            if adapter_risk_category != "ACCEPTABLE_TLS" or adapter_severity != "NONE":
                supporting_reasons.append(f"Adapter risk not clean ({adapter_risk_category}/{adapter_severity}) — cannot fallback to ALLOW")
        else:
            final_decision = "REVIEW"
            final_risk = "LOW"
            decision_source = "CONFIDENCE"
            primary_reason = f"VALID_TLS but SPL confidence {spl_confidence:.2f} < threshold {allow_threshold} (profile: {profile})"
            supporting_reasons.append("Adapter: ACCEPTABLE_TLS")
            supporting_reasons.append(f"SPL decision: {'DENY' if spl_decision else 'ALLOW'} (confidence: {spl_confidence:.2f})")
            supporting_reasons.append(f"Low confidence triggers REVIEW instead of ALLOW (profile: {profile})")
            confidence_source = "SPL"

    # Rule 8: Fallback -> REVIEW
    else:
        final_decision = "REVIEW"
        final_risk = adapter_severity if adapter_severity in ("LOW", "MEDIUM", "HIGH", "CRITICAL") else "LOW"
        decision_source = "COMBINED"
        primary_reason = f"Unhandled combination: {classification} / {adapter_risk_category} (profile: {profile})"
        supporting_reasons.append(f"Adapter risk: {adapter_risk_category} ({adapter_severity})")
        if spl_decision is not None:
            supporting_reasons.append(f"SPL decision: {'DENY' if spl_decision else 'ALLOW'} (confidence: {spl_confidence:.2f})")
        if spl_decision is None:
            confidence_source = "UNAVAILABLE"

    return OrchestratorOutput(
        classification=classification,
        final_decision=final_decision,
        final_risk=final_risk,
        primary_reason=primary_reason,
        supporting_reasons=supporting_reasons,
        decision_source=decision_source,
        fallback_used=fallback_used,
        confidence_source=confidence_source,
        spl_decision=spl_decision,
        spl_confidence=spl_confidence,
        spl_policy_label=spl_policy_label,
        adapter_risk_category=adapter_risk_category,
        adapter_severity=adapter_severity,
        adapter_action_hint=adapter_action_hint,
        ofe_observed=ofe_observed,
    )


def orchestrate(
    inputs: OrchestratorInput,
    profile: OperatingProfile = "balanced",
) -> OrchestratorOutput:
    """Convenience wrapper that unpacks an OrchestratorInput dict."""
    return decide(
        adapter_risk_category=inputs.get("adapter_risk_category", "UNKNOWN_RISK"),
        adapter_severity=inputs.get("adapter_severity", "LOW"),
        adapter_action_hint=inputs.get("adapter_action_hint", "INVESTIGATE"),
        spl_decision=inputs.get("spl_decision"),
        spl_confidence=inputs.get("spl_confidence", 0.0),
        classification=inputs.get("classification", "UNKNOWN_SSL_ERROR"),
        spl_policy_label=inputs.get("spl_policy_label"),
        weakness_flags=inputs.get("weakness_flags"),
        ofe_signals=inputs.get("ofe_signals"),
        profile=profile,
        probe_limited=inputs.get("probe_limited", False),
    )
