"""Schema definitions for the TLS Risk Policy Adapter.

Defines the deterministic mapping from TLS classifications to risk categories,
severities, failure families, and action hints.

The mapping is a sidecar — it does not modify SPL Core, does not learn,
and does not read expectation files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Tuple

TLSClassification = Literal[
    "VALID_TLS",
    "DEPRECATED_TLS_VERSION",
    "REVOKED_CERT",
    "EXPIRED_CERT",
    "SELF_SIGNED_CERT",
    "WRONG_HOST_CERT",
    "UNTRUSTED_CHAIN",
    "INCOMPLETE_CHAIN",
    "WEAK_SIGNATURE_ALGORITHM",
    "WEAK_CIPHER_SUITE",
    "STATIC_RSA_KEY_EXCHANGE",
    "TLS_COMPRESSION_ENABLED",
    "WILDCARD_CERTIFICATE",
    "MISSING_OCSP_STAPLE",
    "DNS_FAILURE",
    "CONNECTION_ERROR",
    "TIMEOUT",
    "TLS_HANDSHAKE_FAILURE",
    "OCSP_UNREACHABLE",
    "UNKNOWN_SSL_ERROR",
]

TLSSeverity = Literal["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

TLSRiskCategory = Literal[
    "ACCEPTABLE_TLS",
    "SECURITY_RISK",
    "AVAILABILITY_RISK",
    "AMBIGUOUS_FAILURE",
    "CHAIN_TRUST_FAILURE",
    "DEPRECATED_PROTOCOL_RISK",
    "UNKNOWN_RISK",
]

TLSFailureFamily = Literal[
    "NONE",
    "CERTIFICATE_TRUST",
    "CHAIN_TRUST",
    "AVAILABILITY",
    "PROTOCOL_WEAKNESS",
    "AMBIGUOUS",
    "UNKNOWN",
]

TLSClassificationLiteral = TLSClassification


@dataclass(frozen=True)
class TLSPolicyEvidence:
    """Structured risk evidence for a single TLS probe classification.

    All fields are deterministic based on the classification string.
    No learning, no expectations, no ground truth.
    """

    classification: TLSClassification
    risk_category: TLSRiskCategory
    severity: TLSSeverity
    failure_family: TLSFailureFamily
    action_hint: str
    policy_reason: str


# Ordered severity levels from lowest to highest risk.
SEVERITY_ORDER: List[TLSSeverity] = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Human-readable policy reasons per classification.
_POLICY_REASONS: Dict[str, str] = {
    "VALID_TLS": "TLS handshake succeeded with valid certificate chain.",
    "REVOKED_CERT": "Certificate has been revoked by the issuing CA (OCSP).",
    "EXPIRED_CERT": "Certificate is expired.",
    "SELF_SIGNED_CERT": "Certificate is self-signed and not trusted.",
    "WRONG_HOST_CERT": "Certificate does not match the requested hostname.",
    "UNTRUSTED_CHAIN": "Certificate chain is complete but root CA is not trusted.",
    "INCOMPLETE_CHAIN": "Server did not send intermediate certificate.",
    "WEAK_SIGNATURE_ALGORITHM": "Certificate uses a weak signature algorithm (e.g., SHA-1).",
    "WEAK_CIPHER_SUITE": "Negotiated a weak cipher suite (RC4, 3DES, NULL, or EXPORT).",
    "STATIC_RSA_KEY_EXCHANGE": "Cipher uses static RSA key exchange without forward secrecy.",
    "TLS_COMPRESSION_ENABLED": "TLS compression enabled; vulnerable to CRIME attack.",
    "WILDCARD_CERTIFICATE": "Certificate uses a wildcard subjectAltName.",
    "MISSING_OCSP_STAPLE": "Server did not provide an OCSP staple.",
    "DNS_FAILURE": "Domain could not be resolved.",
    "CONNECTION_ERROR": "TCP connection failed.",
    "TIMEOUT": "No response within probe timeout window.",
    "TLS_HANDSHAKE_FAILURE": "TLS handshake failed; root cause is ambiguous.",
    "OCSP_UNREACHABLE": "OCSP responder unreachable or timed out; revocation status unknown.",
    "UNKNOWN_SSL_ERROR": "Unrecognized SSL error occurred.",
    "DEPRECATED_TLS_VERSION": "Deprecated TLS version negotiated (TLS 1.0/1.1).",
}

# Action hints per classification.
_ACTION_HINTS: Dict[str, str] = {
    "VALID_TLS": "NONE",
    "REVOKED_CERT": "DENY",
    "EXPIRED_CERT": "RENEW_OR_DENY",
    "SELF_SIGNED_CERT": "REVIEW_OR_DENY",
    "WRONG_HOST_CERT": "DENY",
    "UNTRUSTED_CHAIN": "REVIEW_OR_DENY",
    "INCOMPLETE_CHAIN": "REVIEW_OR_DENY",
    "WEAK_SIGNATURE_ALGORITHM": "REVIEW_OR_DENY",
    "WEAK_CIPHER_SUITE": "MODERNIZE_OR_DENY",
    "STATIC_RSA_KEY_EXCHANGE": "MODERNIZE_OR_DENY",
    "TLS_COMPRESSION_ENABLED": "MODERNIZE_OR_DENY",
    "WILDCARD_CERTIFICATE": "REVIEW",
    "MISSING_OCSP_STAPLE": "REVIEW",
    "DNS_FAILURE": "REVIEW",
    "CONNECTION_ERROR": "REVIEW",
    "TIMEOUT": "REVIEW",
    "TLS_HANDSHAKE_FAILURE": "INVESTIGATE",
    "OCSP_UNREACHABLE": "REVIEW",
    "UNKNOWN_SSL_ERROR": "INVESTIGATE",
    "DEPRECATED_TLS_VERSION": "MODERNIZE_OR_DENY",
}

# The central deterministic map.
RISK_MAP: Dict[str, TLSPolicyEvidence] = {
    "VALID_TLS": TLSPolicyEvidence(
        classification="VALID_TLS",
        risk_category="ACCEPTABLE_TLS",
        severity="NONE",
        failure_family="NONE",
        action_hint="NONE",
        policy_reason=_POLICY_REASONS["VALID_TLS"],
    ),
    "REVOKED_CERT": TLSPolicyEvidence(
        classification="REVOKED_CERT",
        risk_category="SECURITY_RISK",
        severity="CRITICAL",
        failure_family="CERTIFICATE_TRUST",
        action_hint="DENY",
        policy_reason=_POLICY_REASONS["REVOKED_CERT"],
    ),
    "OCSP_UNREACHABLE": TLSPolicyEvidence(
        classification="OCSP_UNREACHABLE",
        risk_category="AVAILABILITY_RISK",
        severity="MEDIUM",
        failure_family="AVAILABILITY",
        action_hint="REVIEW",
        policy_reason=_POLICY_REASONS["OCSP_UNREACHABLE"],
    ),
    "DEPRECATED_TLS_VERSION": TLSPolicyEvidence(
        classification="DEPRECATED_TLS_VERSION",
        risk_category="DEPRECATED_PROTOCOL_RISK",
        severity="HIGH",
        failure_family="PROTOCOL_WEAKNESS",
        action_hint="MODERNIZE_OR_DENY",
        policy_reason=_POLICY_REASONS["DEPRECATED_TLS_VERSION"],
    ),
    "EXPIRED_CERT": TLSPolicyEvidence(
        classification="EXPIRED_CERT",
        risk_category="SECURITY_RISK",
        severity="HIGH",
        failure_family="CERTIFICATE_TRUST",
        action_hint="RENEW_OR_DENY",
        policy_reason=_POLICY_REASONS["EXPIRED_CERT"],
    ),
    "SELF_SIGNED_CERT": TLSPolicyEvidence(
        classification="SELF_SIGNED_CERT",
        risk_category="SECURITY_RISK",
        severity="HIGH",
        failure_family="CERTIFICATE_TRUST",
        action_hint="REVIEW_OR_DENY",
        policy_reason=_POLICY_REASONS["SELF_SIGNED_CERT"],
    ),
    "WRONG_HOST_CERT": TLSPolicyEvidence(
        classification="WRONG_HOST_CERT",
        risk_category="SECURITY_RISK",
        severity="CRITICAL",
        failure_family="CERTIFICATE_TRUST",
        action_hint="DENY",
        policy_reason=_POLICY_REASONS["WRONG_HOST_CERT"],
    ),
    "UNTRUSTED_CHAIN": TLSPolicyEvidence(
        classification="UNTRUSTED_CHAIN",
        risk_category="SECURITY_RISK",
        severity="HIGH",
        failure_family="CHAIN_TRUST",
        action_hint="REVIEW_OR_DENY",
        policy_reason=_POLICY_REASONS["UNTRUSTED_CHAIN"],
    ),
    "INCOMPLETE_CHAIN": TLSPolicyEvidence(
        classification="INCOMPLETE_CHAIN",
        risk_category="CHAIN_TRUST_FAILURE",
        severity="HIGH",
        failure_family="CHAIN_TRUST",
        action_hint="REVIEW_OR_DENY",
        policy_reason=_POLICY_REASONS["INCOMPLETE_CHAIN"],
    ),
    "WEAK_SIGNATURE_ALGORITHM": TLSPolicyEvidence(
        classification="WEAK_SIGNATURE_ALGORITHM",
        risk_category="SECURITY_RISK",
        severity="HIGH",
        failure_family="PROTOCOL_WEAKNESS",
        action_hint="REVIEW_OR_DENY",
        policy_reason=_POLICY_REASONS["WEAK_SIGNATURE_ALGORITHM"],
    ),
    "WEAK_CIPHER_SUITE": TLSPolicyEvidence(
        classification="WEAK_CIPHER_SUITE",
        risk_category="SECURITY_RISK",
        severity="HIGH",
        failure_family="PROTOCOL_WEAKNESS",
        action_hint="MODERNIZE_OR_DENY",
        policy_reason=_POLICY_REASONS["WEAK_CIPHER_SUITE"],
    ),
    "STATIC_RSA_KEY_EXCHANGE": TLSPolicyEvidence(
        classification="STATIC_RSA_KEY_EXCHANGE",
        risk_category="SECURITY_RISK",
        severity="MEDIUM",
        failure_family="PROTOCOL_WEAKNESS",
        action_hint="MODERNIZE_OR_DENY",
        policy_reason=_POLICY_REASONS["STATIC_RSA_KEY_EXCHANGE"],
    ),
    "TLS_COMPRESSION_ENABLED": TLSPolicyEvidence(
        classification="TLS_COMPRESSION_ENABLED",
        risk_category="SECURITY_RISK",
        severity="MEDIUM",
        failure_family="PROTOCOL_WEAKNESS",
        action_hint="MODERNIZE_OR_DENY",
        policy_reason=_POLICY_REASONS["TLS_COMPRESSION_ENABLED"],
    ),
    "WILDCARD_CERTIFICATE": TLSPolicyEvidence(
        classification="WILDCARD_CERTIFICATE",
        risk_category="ACCEPTABLE_TLS",
        severity="LOW",
        failure_family="CERTIFICATE_TRUST",
        action_hint="REVIEW",
        policy_reason=_POLICY_REASONS["WILDCARD_CERTIFICATE"],
    ),
    "MISSING_OCSP_STAPLE": TLSPolicyEvidence(
        classification="MISSING_OCSP_STAPLE",
        risk_category="ACCEPTABLE_TLS",
        severity="LOW",
        failure_family="AVAILABILITY",
        action_hint="REVIEW",
        policy_reason=_POLICY_REASONS["MISSING_OCSP_STAPLE"],
    ),
    "DNS_FAILURE": TLSPolicyEvidence(
        classification="DNS_FAILURE",
        risk_category="AVAILABILITY_RISK",
        severity="MEDIUM",
        failure_family="AVAILABILITY",
        action_hint="REVIEW",
        policy_reason=_POLICY_REASONS["DNS_FAILURE"],
    ),
    "CONNECTION_ERROR": TLSPolicyEvidence(
        classification="CONNECTION_ERROR",
        risk_category="AVAILABILITY_RISK",
        severity="MEDIUM",
        failure_family="AVAILABILITY",
        action_hint="REVIEW",
        policy_reason=_POLICY_REASONS["CONNECTION_ERROR"],
    ),
    "TIMEOUT": TLSPolicyEvidence(
        classification="TIMEOUT",
        risk_category="AVAILABILITY_RISK",
        severity="MEDIUM",
        failure_family="AVAILABILITY",
        action_hint="REVIEW",
        policy_reason=_POLICY_REASONS["TIMEOUT"],
    ),
    "TLS_HANDSHAKE_FAILURE": TLSPolicyEvidence(
        classification="TLS_HANDSHAKE_FAILURE",
        risk_category="AMBIGUOUS_FAILURE",
        severity="MEDIUM",
        failure_family="AMBIGUOUS",
        action_hint="INVESTIGATE",
        policy_reason=_POLICY_REASONS["TLS_HANDSHAKE_FAILURE"],
    ),
    "UNKNOWN_SSL_ERROR": TLSPolicyEvidence(
        classification="UNKNOWN_SSL_ERROR",
        risk_category="UNKNOWN_RISK",
        severity="LOW",
        failure_family="UNKNOWN",
        action_hint="INVESTIGATE",
        policy_reason=_POLICY_REASONS["UNKNOWN_SSL_ERROR"],
    ),
}


def all_classifications() -> List[str]:
    """Return all recognized TLS classification strings."""
    return list(RISK_MAP.keys())
