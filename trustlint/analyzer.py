"""TrustLint core analysis engine — public Python API.

Provides ``analyze``, ``analyze_batch``, ``get_version``, and
``get_classifications`` as the primary programmatic interface.

This module is self-contained within the ``trustlint`` package and does
NOT import from ``scripts``.  All external dependencies are resolved via
lazy imports inside functions to avoid circular-import issues.
"""

from __future__ import annotations

import os
import re
import sys
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from trustlint.infrastructure.tls_probe import probe_domain
from trustlint.infrastructure.error_codes import get_error_code
from tls_policy_adapter import classify_risk
from tls_policy_adapter.classifications import (
    DEPRECATED_TLS_VERSIONS,
    DEPRECATED_TLS_CLASSIFICATION,
)
from decision_orchestrator import decide

logger = logging.getLogger("trustlint")

_DOMAIN_RE = re.compile(
    r"^([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

__version__ = "1.0.0"

# ── Resource Limits ────────────────────────────────────────────────────────
MAX_INPUT_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_DOMAINS = 10_000
MAX_DOMAIN_LENGTH = 253

# ── Recommended Actions ────────────────────────────────────────────────────
_RECOMMENDED_ACTIONS: Dict[str, str] = {
    "VALID_TLS": "No action required.",
    "REVOKED_CERT": "Certificate is revoked — do not trust this connection. Replace the certificate immediately.",
    "EXPIRED_CERT": "Renew or replace the certificate immediately.",
    "SELF_SIGNED_CERT": "Use a certificate issued by a trusted CA unless this is an internal-only system.",
    "WRONG_HOST_CERT": "Replace certificate with one matching the requested hostname.",
    "UNTRUSTED_CHAIN": "Fix the certificate chain — ensure all intermediate certificates are installed on the server.",
    "INCOMPLETE_CHAIN": "Install all missing intermediate certificates on the server.",
    "DNS_FAILURE": "Check DNS records and resolver availability for this domain.",
    "CONNECTION_ERROR": "Check network availability and firewall rules for the target server.",
    "TIMEOUT": "Check network availability, firewall, or server responsiveness. The connection timed out.",
    "TLS_HANDSHAKE_FAILURE": "Check TLS configuration and supported protocol/cipher settings on the server.",
    "DEPRECATED_TLS_VERSION": "Disable deprecated TLS protocols (TLS 1.0/1.1) and require TLS 1.2+ or TLS 1.3.",
    "WEAK_SIGNATURE_ALGORITHM": "Replace certificate signed with a weak algorithm (e.g., SHA-1) with one using a strong algorithm (SHA-256 or better).",
    "WEAK_CIPHER_SUITE": "Disable weak cipher suites (RC4, 3DES, NULL, EXPORT) on the server and configure strong ciphers only (TLS 1.2+ AEAD ciphers).",
    "STATIC_RSA_KEY_EXCHANGE": "Reconfigure server to use ephemeral Diffie-Hellman (DHE or ECDHE) key exchange for forward secrecy.",
    "TLS_COMPRESSION_ENABLED": "Disable TLS compression on the server to mitigate CRIME attack vulnerability.",
    "WILDCARD_CERTIFICATE": "Consider using a non-wildcard certificate to reduce the risk of subdomain impersonation.",
    "MISSING_OCSP_STAPLE": "Enable OCSP stapling on the server to improve revocation checking performance and privacy.",
    "OCSP_UNREACHABLE": "OCSP responder could not be reached — unable to confirm revocation status. Investigate network connectivity to the OCSP responder.",
    "UNKNOWN_SSL_ERROR": "Investigate SSL error details manually — the specific cause could not be determined by automated probing.",
}


# ── Helpers ────────────────────────────────────────────────────────────────


def validate_domain_name(domain: str) -> Tuple[bool, str]:
    """Validate a domain name format.

    Returns (is_valid, error_message).
    """
    if not domain or len(domain) > MAX_DOMAIN_LENGTH:
        return False, "Domain is empty or exceeds 253 characters"
    if not _DOMAIN_RE.match(domain):
        return False, f"Invalid domain format: {domain!r}"
    return True, ""


def _get_recommended_action(classification: str, final_decision: str) -> str:
    if final_decision == "ALLOW":
        return _RECOMMENDED_ACTIONS.get("VALID_TLS", "No action required.")
    return _RECOMMENDED_ACTIONS.get(
        classification,
        "Review the domain manually — no specific automated recommendation available.",
    )


def _get_probe_warnings(
    probe_result: Dict[str, Any],
    classification: str,
) -> List[str]:
    warnings: List[str] = []
    tls_info = probe_result.get("tls") or {}

    if classification == "DNS_FAILURE" and probe_result.get("dns_error"):
        warnings.append(f"DNS resolution failed: {probe_result['dns_error']}")
    if classification == "DEPRECATED_TLS_VERSION":
        ver = tls_info.get("tls_version", "unknown")
        warnings.append(
            f"Deprecated TLS version detected via secondary probe — "
            f"server allows TLS 1.0 or 1.1 (primary negotiated {ver})."
        )
    if tls_info.get("cert_is_expired"):
        warnings.append("Certificate is expired according to the probe.")
    if tls_info.get("cert_chain_complete") is False:
        warnings.append("Certificate chain is incomplete.")
    if tls_info.get("deprecated_tls_check") == "unavailable_on_platform":
        warnings.append(
            "Deprecated TLS check unavailable: TLSv1_1 not supported by local OpenSSL build."
        )
    return warnings


def resolve_classification(probe_result: Dict[str, Any]) -> str:
    """Resolve effective classification, detecting deprecated TLS versions."""
    classification = probe_result.get("classification", "UNKNOWN_SSL_ERROR")
    if classification == "VALID_TLS":
        tls_info = probe_result.get("tls") or {}
        tls_version = (tls_info.get("tls_version") or "").strip().lower()
        if tls_version in DEPRECATED_TLS_VERSIONS:
            return DEPRECATED_TLS_CLASSIFICATION
    return classification


def _build_evidence_artifact(domain: str, probe_result: Dict[str, Any]) -> Dict[str, Any]:
    tls_info = probe_result.get("tls") or {}
    classification = probe_result.get("classification", "")
    cert_not_expired = tls_info.get("cert_is_expired") is not True
    chain_complete = tls_info.get("cert_chain_complete") is not False

    if classification in ("TIMEOUT",):
        status = "timeout"
    elif classification in ("CONNECTION_ERROR", "DNS_FAILURE"):
        status = "error"
    elif classification in ("TLS_HANDSHAKE_FAILURE",):
        status = "partial"
    else:
        status = "ok"

    return {
        "evidence_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": f"tls_probe:{domain}",
        "type": "tls_certificate",
        "data": {
            "valid": cert_not_expired and chain_complete,
            "expiry_days": tls_info.get("cert_expiry_days", 0) or 0,
            "headers": {
                "hsts": None,
                "csp": None,
                "hsts_checked": False,
                "csp_checked": False,
            },
        },
        "transport_meta": {
            "status": status,
            "latency_ms": float(tls_info.get("handshake_time_ms", 0) or 0),
        },
        "tags": [],
        "version": "v7",
    }


# ── Domain File Loading ────────────────────────────────────────────────────


def load_domains_from_file(path: str) -> List[str]:
    """Load domains from a file with resource limits.

    Enforces:
    - Maximum file size (10 MB)
    - Maximum number of domains (10,000)
    - Maximum domain length (253 chars)

    Raises:
        ValueError: If file exceeds size limit or domain count exceeds max.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Domain file not found: {path}")

    file_size = os.path.getsize(path)
    if file_size > MAX_INPUT_FILE_SIZE:
        raise ValueError(
            f"Domain file '{path}' is {file_size} bytes, "
            f"exceeding maximum of {MAX_INPUT_FILE_SIZE} bytes"
        )

    domains: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                if len(stripped) > MAX_DOMAIN_LENGTH:
                    logger.warning(
                        "Skipping domain exceeding %d chars: %s...",
                        MAX_DOMAIN_LENGTH,
                        stripped[:50],
                    )
                    continue
                domains.append(stripped)
                if len(domains) > MAX_DOMAINS:
                    raise ValueError(
                        f"Domain file contains more than {MAX_DOMAINS} domains. "
                        "Reduce the input size or split into multiple files."
                    )
    return domains


def resolve_targets(target: str) -> List[str]:
    if os.path.isfile(target):
        return load_domains_from_file(target)
    return [target.strip()]


# ── Core Analysis ──────────────────────────────────────────────────────────


def analyze_domain(
    domain: str,
    profile: Any = "balanced",
    timeout: float = 10.0,
    ca_store: str = "platform",
    spl_pipeline: Any = None,
    allow_private_targets: bool = False,
) -> Dict[str, Any]:
    """Run full analysis pipeline on a single domain.

    When *spl_pipeline* is provided (an ``EvidencePipeline`` instance), the
    TLS probe result is wrapped as an SPL v7 EvidenceArtifact and processed
    through the pipeline to produce a real *causal_probability* confidence.

    Returns a nested dict with tls_probe, policy_adapter, spl, final sub-objects.
    """
    raw = probe_domain(
        domain,
        ca_store=ca_store,
        timeout=timeout,
        allow_private_targets=allow_private_targets,
    )

    classification = resolve_classification(raw)
    tls_info = raw.get("tls") or {}
    warnings = _get_probe_warnings(raw, classification)

    if tls_info.get("ocsp_error"):
        warnings.append(f"OCSP: {tls_info['ocsp_error']}")
    if tls_info.get("ocsp_status") == "revoked":
        warnings.append("Certificate is revoked according to OCSP check.")
    if tls_info.get("ocsp_status") == "unreachable":
        warnings.append("OCSP responder unreachable — revocation status not confirmed.")
    is_probe_limited = len(warnings) > 0

    try:
        evidence = classify_risk(classification)
    except KeyError:
        evidence = classify_risk("UNKNOWN_SSL_ERROR")

    spl_decision: Optional[bool] = None
    spl_confidence: float = 0.0
    spl_policy_label: Optional[str] = None
    weakness_flags: List[str] = []

    if spl_pipeline is not None:
        try:
            artifact = _build_evidence_artifact(domain, raw)
            spl_pipeline.ingest(artifact)
            result = spl_pipeline.process_one()
            if result is not None:
                spl_decision = bool(result["decision"])
                spl_confidence = float(result["causal_probability"])
                spl_policy_label = "ALLOW" if not spl_decision else "DENY"
                weakness_flags = []
            else:
                weakness_flags = ["pipeline_process_failed"]
        except Exception as e:
            logger.debug("SPL pipeline error for %s: %s", domain, e)
            weakness_flags = ["pipeline_error"]

    out = decide(
        adapter_risk_category=evidence.risk_category,
        adapter_severity=evidence.severity,
        adapter_action_hint=evidence.action_hint,
        spl_decision=spl_decision,
        spl_confidence=spl_confidence,
        classification=classification,
        spl_policy_label=spl_policy_label,
        profile=profile,
        probe_limited=is_probe_limited,
    )

    recommended_action = _get_recommended_action(classification, out["final_decision"])

    return {
        "domain": domain,
        "profile": profile,
        "ca_store": ca_store,
        "spl_active": spl_pipeline is not None,
        "probe_timestamp": raw.get("probe_timestamp", ""),
        "tls_probe": {
            "classification": classification,
            "raw_classification": raw.get("classification", ""),
            "tls_version": tls_info.get("tls_version"),
            "expiry_days": tls_info.get("cert_expiry_days"),
            "resolved_ip": raw.get("resolved_ip"),
            "cert_is_expired": tls_info.get("cert_is_expired"),
            "chain_complete": tls_info.get("cert_chain_complete"),
            "handshake_time_ms": tls_info.get("handshake_time_ms"),
            "ocsp_performed": tls_info.get("ocsp_performed", False),
            "ocsp_stapled": tls_info.get("ocsp_stapled", False),
            "ocsp_status": tls_info.get("ocsp_status"),
            "ocsp_error": tls_info.get("ocsp_error"),
            "ocsp_responder_url": tls_info.get("ocsp_responder_url"),
            "deprecated_tls_check": tls_info.get("deprecated_tls_check"),
            "deprecated_tls_detected": tls_info.get("deprecated_tls_detected", False),
            "warnings": warnings,
            "is_probe_limited": is_probe_limited,
        },
        "policy_adapter": {
            "risk_category": evidence.risk_category,
            "severity": evidence.severity,
            "failure_family": evidence.failure_family,
            "reason": evidence.policy_reason,
            "action_hint": evidence.action_hint,
        },
        "spl": {
            "decision": out.get("spl_decision"),
            "confidence": out.get("spl_confidence"),
            "confidence_source": out.get("confidence_source", "UNAVAILABLE"),
            "weakness_flags": weakness_flags,
        },
        "final": {
            "decision": out["final_decision"],
            "risk": out["final_risk"],
            "source": out["decision_source"],
            "fallback_used": out.get("fallback_used", False),
            "primary_reason": out["primary_reason"],
            "supporting_reasons": out["supporting_reasons"],
            "recommended_action": recommended_action,
            "limitations": warnings,
        },
        "ofe_observed": out.get("ofe_observed", False),
    }


# ── Public Python API ──────────────────────────────────────────────────────


def analyze(
    domain: str,
    profile: Any = "balanced",
    timeout: float = 10.0,
    ca_store: str = "platform",
    allow_private_targets: bool = False,
) -> Dict[str, Any]:
    """Analyze a single domain and return structured results.

    This is the primary Python API for single-domain analysis.
    Results format is identical to CLI output.

    Args:
        domain: Domain name to analyze.
        profile: Decision operating profile ("balanced", "conservative", "strict").
        timeout: Probe timeout in seconds.
        ca_store: CA trust store to use ("platform" or "certifi").
        allow_private_targets: Allow scanning private/internal IPs. Default False.

    Returns:
        Dict with domain, profile, tls_probe, policy_adapter, spl, final sub-objects.

    Raises:
        ValueError: If domain is invalid.
        ConnectionError: If DNS resolution or connection fails.
    """
    valid, err_msg = validate_domain_name(domain)
    if not valid:
        raise ValueError(f"Invalid domain: {err_msg}")
    return analyze_domain(
        domain,
        profile=profile,
        timeout=timeout,
        ca_store=ca_store,
        allow_private_targets=allow_private_targets,
    )


def analyze_batch(
    domains: List[str],
    profile: Any = "balanced",
    timeout: float = 10.0,
    ca_store: str = "platform",
    max_workers: int = 1,
    allow_private_targets: bool = False,
) -> Dict[str, Any]:
    """Analyze multiple domains and return batch results.

    This is the primary Python API for batch analysis.
    Results format includes summary statistics.

    Args:
        domains: List of domain names to analyze.
        profile: Decision operating profile.
        timeout: Probe timeout per domain in seconds.
        ca_store: CA trust store to use.
        max_workers: Number of concurrent workers (default: 1).
        allow_private_targets: Allow scanning private/internal IPs. Default False.

    Returns:
        Dict with results, errors, summary sub-objects.
    """
    if not domains:
        return {
            "results": [],
            "errors": [],
            "summary": {
                "total_domains": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0,
            },
        }

    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for domain in domains:
        try:
            r = analyze(
                domain,
                profile=profile,
                timeout=timeout,
                ca_store=ca_store,
                allow_private_targets=allow_private_targets,
            )
            results.append(r)
        except Exception as e:
            error_code = get_error_code(e)
            errors.append({
                "domain": domain,
                "error_code": error_code.value,
                "error_message": str(e),
                "error_description": error_code.name,
            })

    summary = {
        "total_domains": len(domains),
        "success": len(results),
        "failed": len(errors),
        "skipped": 0,
        "highest_risk": "NONE",
    }

    risk_order = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    highest_idx = 0
    for r in results:
        risk = r["final"]["risk"]
        if risk in risk_order:
            idx = risk_order.index(risk)
            if idx > highest_idx:
                highest_idx = idx
    summary["highest_risk"] = risk_order[highest_idx]

    return {
        "results": results,
        "errors": errors,
        "summary": summary,
    }


def get_version() -> str:
    """Return the current TrustLint version string."""
    return __version__


def get_classifications() -> List[str]:
    """Return list of all valid classification strings."""
    from tls_policy_adapter.classifications import ALL_CLASSIFICATIONS
    return list(ALL_CLASSIFICATIONS)


def compute_exit_code(results: List[Dict[str, Any]]) -> int:
    has_deny = any(r["final"]["decision"] == "DENY" for r in results)
    has_review = any(r["final"]["decision"] == "REVIEW" for r in results)
    if has_deny:
        return 2
    if has_review:
        return 1
    return 0


def compute_summary(results: List[Dict[str, Any]], errors: Optional[List[str]] = None) -> Dict[str, Any]:
    """Compute batch summary statistics."""
    total = len(results)
    allow_count = sum(1 for r in results if r["final"]["decision"] == "ALLOW")
    review_count = sum(1 for r in results if r["final"]["decision"] == "REVIEW")
    deny_count = sum(1 for r in results if r["final"]["decision"] == "DENY")
    probe_limited = sum(1 for r in results if r["tls_probe"]["is_probe_limited"])
    fallback_count = sum(1 for r in results if r["final"].get("fallback_used", False))
    errors_count = sum(1 for r in results if r["tls_probe"]["classification"] == "UNKNOWN_SSL_ERROR")
    risk_order = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    highest_idx = 0
    for r in results:
        risk = r["final"]["risk"]
        if risk in risk_order:
            idx = risk_order.index(risk)
            if idx > highest_idx:
                highest_idx = idx
    highest_risk = risk_order[highest_idx]

    summary: Dict[str, Any] = {
        "total_domains": total,
        "allow": allow_count,
        "review": review_count,
        "deny": deny_count,
        "fallback": fallback_count,
        "probe_limited": probe_limited,
        "probe_errors": errors_count,
        "highest_risk": highest_risk,
    }

    if errors:
        summary["failed_domains"] = len(errors)
        summary["error_details"] = errors

    return summary
