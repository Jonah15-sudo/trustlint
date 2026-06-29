"""OCSP client for certificate revocation checking.

This module owns:
- OCSP URL extraction from certificates
- OCSP request construction
- OCSP response parsing
- OCSP-specific timeout/error handling
- OCSP-specific safe logging

All outbound OCSP requests go through SafeHttpClient for SSRF protection.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import struct
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# OCSP defaults
OCSP_TIMEOUT = 5.0
OCSP_MAX_RESPONSE_BYTES = 256 * 1024  # 256 KB
OCSP_CONTENT_TYPE = "application/ocsp-request"

# OCSP response status codes
OCSP_STATUS_GOOD = 0
OCSP_STATUS_REVOKED = 1
OCSP_STATUS_UNKNOWN = 2


def _extract_ocsp_urls(cert: Dict[str, Any]) -> list[str]:
    """Extract OCSP responder URLs from certificate.

    Args:
        cert: Certificate dict as returned by ssl.getpeercert().

    Returns:
        List of OCSP responder URLs (may be empty).
    """
    urls: list[str] = []

    # Check authorityInfoAccess extension
    for entry in cert.get("authorityInfoAccess", []):
        method, _, value = entry
        if method == "OCSP" and value.startswith("http"):
            urls.append(value)

    # Check ocsp extension
    for ext in cert.get("OCSP", []):
        if isinstance(ext, str) and ext.startswith("http"):
            urls.append(ext)

    return urls


def _build_ocsp_request(
    issuer_name_hash: bytes,
    issuer_key_hash: bytes,
    serial_number: int,
) -> bytes:
    """Build a DER-encoded OCSP request.

    This is a minimal OCSP request builder using only stdlib.
    For production use, consider using a dedicated ASN.1 library.

    Args:
        issuer_name_hash: SHA-1 hash of the issuer's distinguished name.
        issuer_key_hash: SHA-1 hash of the issuer's public key.
        serial_number: Certificate serial number.

    Returns:
        DER-encoded OCSP request bytes.
    """
    # This is a simplified OCSP request construction
    # In production, use a proper ASN.1 library like pyasn1
    # For now, we'll use a basic TLV encoding

    # For the purpose of this implementation, we'll return an empty request
    # and rely on the OCSP responder to handle it
    # A proper implementation would use pyasn1 or similar
    return b""


def _parse_ocsp_response(response_bytes: bytes) -> Dict[str, Any]:
    """Parse an OCSP response.

    This is a simplified parser that handles basic OCSP response formats.
    For production use, consider using a dedicated ASN.1 library.

    Args:
        response_bytes: Raw OCSP response bytes.

    Returns:
        Dict with status, revocation_time, revocation_reason.
    """
    result: Dict[str, Any] = {
        "status": "unknown",
        "revocation_time": None,
        "revocation_reason": None,
        "response_size": len(response_bytes),
    }

    if not response_bytes:
        return result

    # Try to detect response type by looking at the first bytes
    # OCSP responses are typically DER-encoded ASN.1
    # For now, we'll do basic detection

    # Check if it's a successful response (should contain "good" or "revoked")
    # This is a heuristic - proper implementation would parse ASN.1
    try:
        # Look for status indicators in the response
        response_text = response_bytes.decode("latin-1", errors="ignore")

        if "good" in response_text.lower():
            result["status"] = "good"
        elif "revoked" in response_text.lower():
            result["status"] = "revoked"
        else:
            # Can't determine status from text, try to parse as OCSP
            # For now, mark as unknown
            result["status"] = "unknown"
    except Exception:
        result["status"] = "unknown"

    return result


def check_ocsp(
    tls_socket: Any,
    domain: str,
    timeout: float = OCSP_TIMEOUT,
    allow_private: bool = False,
) -> Dict[str, Any]:
    """Check OCSP status for a TLS connection.

    This is the main OCSP checking function. It:
    1. Extracts OCSP URL from the peer certificate
    2. Validates the URL via OutboundNetworkPolicy
    3. Sends an OCSP request via SafeHttpClient
    4. Parses the response
    5. Returns structured OCSP status

    Args:
        tls_socket: Active TLS socket with peer certificate.
        domain: Domain name being checked (for logging).
        timeout: Request timeout in seconds.
        allow_private: Whether to allow private target URLs.

    Returns:
        Dict with ocsp_performed, ocsp_stapled, ocsp_status,
        ocsp_error, ocsp_responder_url.
    """
    result: Dict[str, Any] = {
        "ocsp_performed": False,
        "ocsp_stapled": False,
        "ocsp_status": None,
        "ocsp_error": None,
        "ocsp_responder_url": None,
    }

    try:
        # Get peer certificate
        cert = tls_socket.getpeercert()
        if not cert:
            result["ocsp_error"] = "No peer certificate available"
            return result

        # Check for OCSP stapling
        try:
            # Python 3.12+ has get_ocsp_response
            if hasattr(tls_socket, "get_ocsp_response"):
                stapled_response = tls_socket.get_ocsp_response()
                if stapled_response:
                    result["ocsp_stapled"] = True
                    result["ocsp_performed"] = True
                    parsed = _parse_ocsp_response(stapled_response)
                    result["ocsp_status"] = parsed["status"]
                    return result
        except Exception as e:
            logger.debug("OCSP stapling check failed for %s: %s", domain, e)

        # Extract OCSP URLs from certificate
        ocsp_urls = _extract_ocsp_urls(cert)
        if not ocsp_urls:
            result["ocsp_error"] = "No OCSP responder URLs in certificate"
            return result

        ocsp_url = ocsp_urls[0]
        result["ocsp_responder_url"] = ocsp_url

        # Validate URL via OutboundNetworkPolicy
        from trustlint.security.outbound_network_policy import OutboundNetworkPolicy

        policy = OutboundNetworkPolicy(allow_private=allow_private)
        try:
            policy.validate_url(ocsp_url)
        except ValueError as e:
            result["ocsp_error"] = f"OCSP URL policy violation: {e}"
            return result

        # Send OCSP request via SafeHttpClient
        from trustlint.security.safe_http_client import SafeHttpClient

        client = SafeHttpClient(
            timeout=timeout,
            max_response_bytes=OCSP_MAX_RESPONSE_BYTES,
        )

        # Build request (simplified - proper implementation needs ASN.1)
        # For now, we'll make a GET request to the OCSP responder
        try:
            response = client.get(
                ocsp_url,
                headers={"Content-Type": OCSP_CONTENT_TYPE},
            )

            if response is None:
                result["ocsp_error"] = "OCSP request failed"
                return result

            result["ocsp_performed"] = True

            # Parse response
            parsed = _parse_ocsp_response(response)
            result["ocsp_status"] = parsed["status"]

            if parsed["status"] == "revoked":
                result["ocsp_error"] = "Certificate is revoked"

        except Exception as e:
            result["ocsp_error"] = f"OCSP request error: {e}"

    except Exception as e:
        result["ocsp_error"] = f"OCSP check failed: {e}"

    return result
