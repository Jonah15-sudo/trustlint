"""TrustLint TLS probing infrastructure.

Implements probe_domain() and supporting functions for TLS analysis.
This module provides the core TLS probing functionality that was previously in
scripts/run_local_tls_validation.py, now properly contained in the package.
"""

import json
import logging
import socket
import ssl
import time as _time
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from trustlint.infrastructure.ocsp import check_ocsp

logger = logging.getLogger(__name__)

# Constants
PROBE_TIMEOUT = 10.0
RATE_LIMIT_SECONDS = 1.0
DEFAULT_PORT = 443
REPORT_DIR = "reports/local_real_validation"

# Use canonical classifications from tls_policy_adapter.classifications
import tls_policy_adapter.classifications

CLASSIFICATION = dict(tls_policy_adapter.classifications.CLASSIFICATION_TO_OVERALL_STATUS)
CLASSIFICATION_ORDER = list(tls_policy_adapter.classifications.ALL_CLASSIFICATIONS)

EXPECTED_LABELS_FILE = "datasets/real_tls_mixed_expected.json"


def _resolve_domain(domain: str) -> Tuple[Optional[str], Optional[str]]:
    """Resolve domain to IP address with error handling."""
    try:
        addrs = socket.getaddrinfo(domain, DEFAULT_PORT, socket.AF_INET, socket.SOCK_STREAM)
        if addrs:
            return addrs[0][4][0], None
        return None, "no address records"
    except socket.gaierror as e:
        return None, f"DNS resolution failed: {e}"
    except OSError as e:
        return None, f"socket error: {e}"


def _classify_ssl_error(err_msg: str, chain_length: Optional[int] = None) -> str:
    """Classify SSL errors into standardized error codes."""
    msg_lower = err_msg.lower()
    if "expired" in msg_lower:
        return "EXPIRED_CERT"
    if "self-signed certificate in certificate chain" in msg_lower:
        return "UNTRUSTED_CHAIN"
    if "self-signed" in msg_lower or "self signed" in msg_lower:
        return "SELF_SIGNED_CERT"
    if "hostname mismatch" in msg_lower or "doesn't match" in msg_lower:
        return "WRONG_HOST_CERT"
    if "dns" in msg_lower and ("record" in msg_lower or "name" in msg_lower or "match" in msg_lower):
        return "WRONG_HOST_CERT"
    if "too weak" in msg_lower or "digest algorithm" in msg_lower:
        return "WEAK_SIGNATURE_ALGORITHM"
    if "unable to get local issuer certificate" in msg_lower:
        if chain_length is not None and chain_length <= 1:
            return "INCOMPLETE_CHAIN"
        return "UNTRUSTED_CHAIN"
    if "certificate verify failed" in msg_lower:
        if "unable" in msg_lower:
            if chain_length is not None and chain_length <= 1:
                return "INCOMPLETE_CHAIN"
            return "UNTRUSTED_CHAIN"
        return "UNKNOWN_SSL_ERROR"
    if "bad dh value" in msg_lower or "dh key too small" in msg_lower:
        return "TLS_HANDSHAKE_FAILURE"
    if "sslv3" in msg_lower or "tlsv1" in msg_lower:
        return "TLS_HANDSHAKE_FAILURE"
    if "handshake" in msg_lower or "protocol" in msg_lower:
        return "TLS_HANDSHAKE_FAILURE"
    if "cipher" in msg_lower or "key" in msg_lower:
        return "TLS_HANDSHAKE_FAILURE"
    if "no shared cipher" in msg_lower:
        return "TLS_HANDSHAKE_FAILURE"
    return "UNKNOWN_SSL_ERROR"


def _create_tls_context(ca_store: str = "platform") -> ssl.SSLContext:
    """Create and configure TLS context for client connections."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    if ca_store == "certifi":
        try:
            import certifi
            context.load_verify_locations(cafile=certifi.where())
        except ImportError:
            pass
    context.load_default_certs()
    return context


def probe_domain(
    domain: str,
    ca_store: str = "platform",
    timeout: float = 10.0,
    allow_private_targets: bool = False,
) -> Dict[str, Any]:
    """Probe a single domain for TLS configuration and certificate status.

    Args:
        domain: Domain name to probe.
        ca_store: CA trust store (\"platform\" or \"certifi\").
        timeout: Connection timeout in seconds.
        allow_private_targets: If True, allow scanning private/internal IPs.
            Default False for safety.

    Returns:
        Dict with domain, probe info, tls info, and classification.
    """
    from trustlint.security.target_policy import TargetScanPolicy

    domain = domain.strip().lower()
    result: Dict[str, Any] = {
        "domain": domain,
        "probe_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "resolved_ip": None,
        "dns_error": None,
        "tls": None,
        "classification": None,
        "ca_store": ca_store,
    }

    ip, dns_err = _resolve_domain(domain)
    if dns_err:
        result["dns_error"] = dns_err
        result["classification"] = "DNS_FAILURE"
        return result

    scan_policy = TargetScanPolicy(allow_private=allow_private_targets)
    try:
        scan_policy.validate_ip(ip)
    except ValueError as e:
        result["dns_error"] = f"Target policy violation: {e}"
        result["classification"] = "CONNECTION_ERROR"
        return result

    result["resolved_ip"] = ip
    result["tls"] = _attempt_tls_handshake(domain, ip, ca_store, timeout)

    tls_info = result["tls"]
    if tls_info.get("error_category"):
        result["classification"] = tls_info["error_category"]
    elif tls_info.get("cert_is_expired"):
        result["classification"] = "EXPIRED_CERT"
    elif tls_info.get("cert_is_self_signed"):
        result["classification"] = "SELF_SIGNED_CERT"
    else:
        result["classification"] = "VALID_TLS"

    return result


def _attempt_tls_handshake(domain: str, ip: str, ca_store: str = "platform", timeout: float = 10.0) -> Dict[str, Any]:
    """Attempt TLS handshake and return detailed connection information."""
    context = _create_tls_context(ca_store)

    info: Dict[str, Any] = {
        "domain": domain,
        "ip": ip,
        "port": DEFAULT_PORT,
        "tls_version": None,
        "cert_is_expired": None,
        "cert_is_self_signed": None,
        "error_category": None,
        "error": None,
    }

    t0 = _time.monotonic()
    try:
        with socket.create_connection((ip, DEFAULT_PORT), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as tls:
                info["handshake_time_ms"] = round((_time.monotonic() - t0) * 1000, 1)
                info["tls_version"] = tls.version()
                cert = tls.getpeercert()
                if cert:
                    if any(after.startswith("Jan 1 00:00:00 1970") for _, after in cert.get("notAfter", [])):
                        info["cert_is_expired"] = True
                    info["cert_is_self_signed"] = True
    except ssl.SSLCertVerificationError as e:
        info["handshake_time_ms"] = round((_time.monotonic() - t0) * 1000, 1)
        info["error"] = str(e)
        info["error_category"] = _classify_ssl_error(str(e))
    except socket.timeout:
        info["handshake_time_ms"] = round((_time.monotonic() - t0) * 1000, 1)
        info["error"] = f"timeout after {timeout}s"
        info["error_category"] = "TIMEOUT"
    except Exception as e:
        info["handshake_time_ms"] = round((_time.monotonic() - t0) * 1000, 1)
        info["error"] = str(e)
        info["error_category"] = "CONNECTION_ERROR"

    return info
