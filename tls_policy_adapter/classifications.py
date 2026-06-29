"""Canonical TLS classification definitions — single source of truth.

All classification strings, deprecated TLS version sets, severity mappings,
and risk categories are defined here. Other modules should import from this
module rather than defining their own copies.

Exports:
    ALL_CLASSIFICATIONS: Tuple of all valid classification strings.
    DEPRECATED_TLS_VERSIONS: Set of lowercase deprecated TLS version strings.
    DEPRECATED_TLS_CLASSIFICATION: The classification string for deprecated TLS.
    CLASSIFICATION_SEVERITY: Mapping from classification to severity level.
    CLASSIFICATION_RISK_CATEGORY: Mapping from classification to risk category.
    CLASSIFICATION_TO_OVERALL_STATUS: Mapping from classification to overall status string.
    get_classification_severity: Get severity for a classification.
    get_classification_risk_category: Get risk category for a classification.
    is_valid_classification: Check if a classification string is valid.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Optional, Set, Tuple

# ── All valid classification strings ────────────────────────────────────────
# This is the canonical list. Order matters for reporting.
ALL_CLASSIFICATIONS: Tuple[str, ...] = (
    "VALID_TLS",
    "DEPRECATED_TLS_VERSION",
    "REVOKED_CERT",
    "DNS_FAILURE",
    "TIMEOUT",
    "CONNECTION_ERROR",
    "TLS_HANDSHAKE_FAILURE",
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
    "OCSP_UNREACHABLE",
    "UNKNOWN_SSL_ERROR",
)

# Fast lookup set
_VALID_CLASSIFICATIONS: FrozenSet[str] = frozenset(ALL_CLASSIFICATIONS)

# ── Deprecated TLS version strings ──────────────────────────────────────────
# Case-insensitive set of TLS version strings considered deprecated.
# Includes both "TLSv1" and "TLSv1.0" since different APIs use different names.
DEPRECATED_TLS_VERSIONS: FrozenSet[str] = frozenset({
    "tlsv1",
    "tlsv1.0",
    "tlsv1.1",
    "tls1",
    "tls1.0",
    "tls1.1",
})

# The classification string used when deprecated TLS is detected.
DEPRECATED_TLS_CLASSIFICATION: str = "DEPRECATED_TLS_VERSION"

# ── Severity mapping ────────────────────────────────────────────────────────
# Maps each classification to its canonical severity level.
CLASSIFICATION_SEVERITY: Dict[str, str] = {
    "VALID_TLS": "NONE",
    "DEPRECATED_TLS_VERSION": "HIGH",
    "REVOKED_CERT": "CRITICAL",
    "DNS_FAILURE": "MEDIUM",
    "TIMEOUT": "MEDIUM",
    "CONNECTION_ERROR": "MEDIUM",
    "TLS_HANDSHAKE_FAILURE": "MEDIUM",
    "EXPIRED_CERT": "HIGH",
    "SELF_SIGNED_CERT": "HIGH",
    "WRONG_HOST_CERT": "CRITICAL",
    "UNTRUSTED_CHAIN": "HIGH",
    "INCOMPLETE_CHAIN": "HIGH",
    "WEAK_SIGNATURE_ALGORITHM": "HIGH",
    "WEAK_CIPHER_SUITE": "HIGH",
    "STATIC_RSA_KEY_EXCHANGE": "MEDIUM",
    "TLS_COMPRESSION_ENABLED": "MEDIUM",
    "WILDCARD_CERTIFICATE": "LOW",
    "MISSING_OCSP_STAPLE": "LOW",
    "OCSP_UNREACHABLE": "MEDIUM",
    "UNKNOWN_SSL_ERROR": "LOW",
}

# ── Risk category mapping ───────────────────────────────────────────────────
CLASSIFICATION_RISK_CATEGORY: Dict[str, str] = {
    "VALID_TLS": "ACCEPTABLE_TLS",
    "DEPRECATED_TLS_VERSION": "DEPRECATED_PROTOCOL_RISK",
    "REVOKED_CERT": "SECURITY_RISK",
    "DNS_FAILURE": "AVAILABILITY_RISK",
    "TIMEOUT": "AVAILABILITY_RISK",
    "CONNECTION_ERROR": "AVAILABILITY_RISK",
    "TLS_HANDSHAKE_FAILURE": "AMBIGUOUS_FAILURE",
    "EXPIRED_CERT": "SECURITY_RISK",
    "SELF_SIGNED_CERT": "SECURITY_RISK",
    "WRONG_HOST_CERT": "SECURITY_RISK",
    "UNTRUSTED_CHAIN": "SECURITY_RISK",
    "INCOMPLETE_CHAIN": "CHAIN_TRUST_FAILURE",
    "WEAK_SIGNATURE_ALGORITHM": "SECURITY_RISK",
    "WEAK_CIPHER_SUITE": "SECURITY_RISK",
    "STATIC_RSA_KEY_EXCHANGE": "SECURITY_RISK",
    "TLS_COMPRESSION_ENABLED": "SECURITY_RISK",
    "WILDCARD_CERTIFICATE": "ACCEPTABLE_TLS",
    "MISSING_OCSP_STAPLE": "ACCEPTABLE_TLS",
    "OCSP_UNREACHABLE": "AVAILABILITY_RISK",
    "UNKNOWN_SSL_ERROR": "UNKNOWN_RISK",
}

# ── Overall status mapping ──────────────────────────────────────────────────
# Maps classification to the overall_status string used in probe results.
CLASSIFICATION_TO_OVERALL_STATUS: Dict[str, str] = {
    "VALID_TLS": "valid",
    "DEPRECATED_TLS_VERSION": "tls_deprecated",
    "REVOKED_CERT": "cert_revoked",
    "DNS_FAILURE": "dns_failure",
    "TIMEOUT": "timeout",
    "CONNECTION_ERROR": "connection_error",
    "TLS_HANDSHAKE_FAILURE": "tls_handshake_failure",
    "EXPIRED_CERT": "cert_expired",
    "SELF_SIGNED_CERT": "self_signed_cert",
    "WRONG_HOST_CERT": "wrong_host_cert",
    "UNTRUSTED_CHAIN": "untrusted_chain",
    "INCOMPLETE_CHAIN": "incomplete_chain",
    "WEAK_SIGNATURE_ALGORITHM": "weak_signature",
    "WEAK_CIPHER_SUITE": "weak_cipher",
    "STATIC_RSA_KEY_EXCHANGE": "static_rsa",
    "TLS_COMPRESSION_ENABLED": "compression_enabled",
    "WILDCARD_CERTIFICATE": "wildcard_cert",
    "MISSING_OCSP_STAPLE": "missing_ocsp_staple",
    "OCSP_UNREACHABLE": "ocsp_unreachable",
    "UNKNOWN_SSL_ERROR": "unknown_ssl_error",
}

# ── Public helper functions ─────────────────────────────────────────────────


def get_classification_severity(classification: str) -> str:
    """Get the canonical severity for a classification string.

    Returns "LOW" for unknown classifications.
    """
    return CLASSIFICATION_SEVERITY.get(classification, "LOW")


def get_classification_risk_category(classification: str) -> str:
    """Get the canonical risk category for a classification string.

    Returns "UNKNOWN_RISK" for unknown classifications.
    """
    return CLASSIFICATION_RISK_CATEGORY.get(classification, "UNKNOWN_RISK")


def is_valid_classification(classification: str) -> bool:
    """Check if a classification string is valid."""
    return classification in _VALID_CLASSIFICATIONS


def is_deprecated_tls_version(version_string: str) -> bool:
    """Check if a TLS version string represents a deprecated version.

    Case-insensitive comparison.
    """
    return version_string.lower() in DEPRECATED_TLS_VERSIONS
