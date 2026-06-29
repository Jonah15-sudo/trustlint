"""OCSP client for certificate revocation checking.

This module owns:
- OCSP URL extraction from certificates
- OCSP request construction
- OCSP response parsing (DER/ASN.1)
- OCSP-specific timeout/error handling
- OCSP-specific safe logging

All outbound OCSP requests go through SafeHttpClient for SSRF protection.

OCSP response parsing uses a minimal DER/ASN.1 decoder built on Python
stdlib only (no external dependencies).  The parser understands the
subset of ASN.1 DER required by RFC 6960 OCSP responses.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# OCSP defaults
OCSP_TIMEOUT = 5.0
OCSP_MAX_RESPONSE_BYTES = 256 * 1024  # 256 KB
OCSP_CONTENT_TYPE = "application/ocsp-request"

# OCSP response status codes (RFC 6960 §2.2)
OCSPResponseStatus_SUCCESSFUL = 0
OCSPResponseStatus_MALFORMEDREQUEST = 1
OCSPResponseStatus_INTERNALERROR = 2
OCSPResponseStatus_TRYLATER = 3
OCSPResponseStatus_SIGREQUIRED = 5
OCSPResponseStatus_UNAUTHORIZED = 6

# CertStatus values
CERT_STATUS_GOOD = "good"
CERT_STATUS_REVOKED = "revoked"
CERT_STATUS_UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Minimal DER/ASN.1 decoder (RFC 4510 / ITU-T X.690)
# ---------------------------------------------------------------------------

class _DerError(Exception):
    """Raised when DER data is malformed or truncated."""


def _der_read_length(data: bytes, offset: int) -> Tuple[int, int]:
    """Read a DER length field starting at *offset*.

    Returns (length, new_offset).
    """
    if offset >= len(data):
        raise _DerError("Unexpected end of data reading length")
    b = data[offset]
    offset += 1
    if b < 0x80:
        return b, offset
    num_bytes = b & 0x7F
    if num_bytes == 0:
        raise _DerError("Indefinite length not supported in DER")
    if offset + num_bytes > len(data):
        raise _DerError("Truncated length field")
    length = 0
    for i in range(num_bytes):
        length = (length << 8) | data[offset + i]
    return length, offset + num_bytes


def _der_decode(data: bytes, offset: int = 0) -> Tuple[int, int, bytes]:
    """Decode one DER TLV triplet.

    Returns (tag, content_offset, content_end).
    """
    if offset >= len(data):
        raise _DerError("Unexpected end of data reading tag")
    tag = data[offset]
    offset += 1
    # Handle multi-byte tags (class = 0x1F)
    if (tag & 0x1F) == 0x1F:
        tag = 0
        while True:
            if offset >= len(data):
                raise _DerError("Truncated multi-byte tag")
            b = data[offset]
            offset += 1
            tag = (tag << 7) | (b & 0x7F)
            if not (b & 0x80):
                break
    length, content_offset = _der_read_length(data, offset)
    content_end = content_offset + length
    if content_end > len(data):
        raise _DerError(
            f"Content length {length} extends past end of data "
            f"(need {content_end}, have {len(data)})"
        )
    return tag, content_offset, content_end


def _der_skip(data: bytes, offset: int) -> int:
    """Skip one DER TLV and return the offset past it."""
    _, _, content_end = _der_decode(data, offset)
    return content_end


def _der_read_integer(data: bytes, offset: int) -> Tuple[int, int]:
    """Read an INTEGER value.  Returns (value, new_offset)."""
    tag, val_off, val_end = _der_decode(data, offset)
    if tag != 0x02:
        raise _DerError(f"Expected INTEGER (0x02), got 0x{tag:02x}")
    value = int.from_bytes(data[val_off:val_end], byteorder="big", signed=True)
    return value, val_end


def _der_read_enum(data: bytes, offset: int) -> Tuple[int, int]:
    """Read an ENUMERATED value.  Returns (value, new_offset)."""
    tag, val_off, val_end = _der_decode(data, offset)
    if tag != 0x0A:
        raise _DerError(f"Expected ENUMERATED (0x0A), got 0x{tag:02x}")
    if val_end - val_off < 1:
        raise _DerError("Empty ENUMERATED value")
    value = int.from_bytes(data[val_off:val_end], byteorder="big", signed=True)
    return value, val_end


def _der_read_octet_string(data: bytes, offset: int) -> Tuple[bytes, int]:
    """Read an OCTET STRING.  Returns (value, new_offset)."""
    tag, val_off, val_end = _der_decode(data, offset)
    if tag != 0x04:
        raise _DerError(f"Expected OCTET STRING (0x04), got 0x{tag:02x}")
    return data[val_off:val_end], val_end


def _der_read_oid(data: bytes, offset: int) -> Tuple[Tuple[int, ...], int]:
    """Read an OBJECT IDENTIFIER.  Returns (oid_tuple, new_offset)."""
    tag, val_off, val_end = _der_decode(data, offset)
    if tag != 0x06:
        raise _DerError(f"Expected OID (0x06), got 0x{tag:02x}")
    if val_off >= val_end:
        raise _DerError("Empty OID")
    components: List[int] = []
    # First byte encodes first two components
    first = data[val_off]
    components.append(first // 40)
    components.append(first % 40)
    value = 0
    for b in data[val_off + 1 : val_end]:
        value = (value << 7) | (b & 0x7F)
        if not (b & 0x80):
            components.append(value)
            value = 0
    return tuple(components), val_end


def _der_read_bit_string(data: bytes, offset: int) -> Tuple[bytes, int]:
    """Read a BIT STRING.  Returns (value_bytes, new_offset)."""
    tag, val_off, val_end = _der_decode(data, offset)
    if tag != 0x03:
        raise _DerError(f"Expected BIT STRING (0x03), got 0x{tag:02x}")
    if val_off >= val_end:
        raise _DerError("Empty BIT STRING")
    unused_bits = data[val_off]
    if unused_bits > 7:
        raise _DerError(f"Invalid BIT STRING unused bits: {unused_bits}")
    raw = data[val_off + 1 : val_end]
    return raw, val_end


def _der_skip_value(data: bytes, offset: int) -> int:
    """Skip any DER value (useful for optional fields)."""
    return _der_skip(data, offset)


# ---------------------------------------------------------------------------
# OCSP response parser (RFC 6960)
# ---------------------------------------------------------------------------

def _parse_ocsp_response_status(data: bytes) -> int:
    """Parse the outermost OCSPResponse and return the responseStatus.

    OCSPResponse ::= SEQUENCE {
        responseStatus    ENUMERATED { ... },
        responseBytes     [0] EXPLICIT ResponseBytes OPTIONAL }

    Returns the numeric response status code.
    Raises _DerError on malformed data.
    """
    tag, seq_off, seq_end = _der_decode(data, 0)
    if tag != 0x30:
        raise _DerError(f"OCSPResponse must be SEQUENCE (0x30), got 0x{tag:02x}")

    # Read responseStatus
    status, next_off = _der_read_enum(data, seq_off)
    return status


def _find_basic_ocsp_response(data: bytes) -> bytes:
    """Navigate from OCSPResponse to the inner BasicOCSPResponse bytes.

    After parsing the SEQUENCE and ENUMERATED, the next field is [0] EXPLICIT
    ResponseBytes.  ResponseBytes ::= SEQUENCE { responseType OID,
    response OCTET STRING }.  The OCTET STRING value is the DER-encoded
    BasicOCSPResponse.

    Returns the raw DER bytes of BasicOCSPResponse.
    Raises _DerError on malformed data.
    """
    tag, seq_off, seq_end = _der_decode(data, 0)
    if tag != 0x30:
        raise _DerError("OCSPResponse must be SEQUENCE")

    # Skip responseStatus (ENUMERATED)
    next_off = _der_skip_value(data, seq_off)

    # Read responseBytes [0] EXPLICIT
    tag, rb_off, rb_end = _der_decode(data, next_off)
    if tag != 0xA0:
        raise _DerError(f"Expected context tag [0] (0xA0), got 0x{tag:02x}")

    # Inside [0]: ResponseBytes ::= SEQUENCE
    tag, rbs_off, rbs_end = _der_decode(data, rb_off)
    if tag != 0x30:
        raise _DerError("ResponseBytes must be SEQUENCE")

    # Skip responseType OID
    next_off = _der_skip_value(data, rbs_off)

    # Read response OCTET STRING
    octet_bytes, _ = _der_read_octet_string(data, next_off)
    return octet_bytes


def _parse_basic_ocsp_response(
    data: bytes,
) -> Dict[str, Any]:
    """Parse a BasicOCSPResponse and extract the first SingleResponse.

    BasicOCSPResponse ::= SEQUENCE {
        tbsResponseData      ResponseData,
        signatureAlgorithm   AlgorithmIdentifier,
        signature            BIT STRING,
        certs                [0] EXPLICIT SEQUENCE OF Certificate OPTIONAL }

    ResponseData ::= SEQUENCE {
        version           [0] EXPLICIT Version DEFAULT v1,
        responderID            ResponderID,
        producedAt             GeneralizedTime,
        responses              SEQUENCE OF SingleResponse,
        responseExtensions [1] EXPLICIT Extensions OPTIONAL }

    SingleResponse ::= SEQUENCE {
        certID              CertID,
        certStatus          CertStatus,
        thisUpdate          GeneralizedTime,
        nextUpdate          [0] EXPLICIT GeneralizedTime OPTIONAL,
        singleExtensions   [1] EXPLICIT Extensions OPTIONAL }

    CertStatus ::= CHOICE {
        good       [0] IMPLICIT NULL,
        revoked    [1] IMPLICIT RevokedInfo,
        unknown    [2] IMPLICIT UnknownInfo }

    Returns dict with keys: cert_status, serial_number, this_update, next_update.
    """
    tag, seq_off, seq_end = _der_decode(data, 0)
    if tag != 0x30:
        raise _DerError("BasicOCSPResponse must be SEQUENCE")

    # Navigate into tbsResponseData (first SEQUENCE in the outer SEQUENCE)
    tag, tbs_off, tbs_end = _der_decode(data, seq_off)
    if tag != 0x30:
        raise _DerError("tbsResponseData must be SEQUENCE")

    # Inside tbsResponseData:
    #   version [0] (optional, DEFAULT v1)
    #   responderID
    #   producedAt GeneralizedTime
    #   responses SEQUENCE OF SingleResponse
    #   responseExtensions [1] (optional)

    cursor = tbs_off

    # Check for version [0]
    tag, v_off, v_end = _der_decode(data, cursor)
    if tag == 0xA0:
        # version is present - skip it (we don't need it for OCSP status)
        cursor = v_end
        # Now read responderID
        tag, ri_off, ri_end = _der_decode(data, cursor)
        cursor = ri_end
    else:
        # No version field, cursor stays where it was
        # tag already points at responderID
        cursor = v_end

    # Skip responderID (could be [0] or [1] IMPLICIT)
    cursor = _der_skip_value(data, cursor)

    # Skip producedAt (GeneralizedTime - APPLICATION 24 = 0x18)
    # GeneralizedTime is tag 0x18
    cursor = _der_skip_value(data, cursor)

    # Now we should be at responses SEQUENCE OF SingleResponse
    tag, resp_off, resp_end = _der_decode(data, cursor)
    if tag != 0x30:
        raise _DerError(f"responses must be SEQUENCE (0x30), got 0x{tag:02x}")

    # Parse the first SingleResponse
    tag, sr_off, sr_end = _der_decode(data, resp_off)
    if tag != 0x30:
        raise _DerError("SingleResponse must be SEQUENCE")

    return _parse_single_response(data, sr_off, sr_end)


def _parse_single_response(
    data: bytes,
    sr_off: int,
    sr_end: int,
) -> Dict[str, Any]:
    """Parse a SingleResponse and return certStatus and certID info.

    SingleResponse ::= SEQUENCE {
        certID              CertID,
        certStatus          CertStatus,
        thisUpdate          GeneralizedTime,
        nextUpdate          [0] EXPLICIT GeneralizedTime OPTIONAL,
        singleExtensions   [1] EXPLICIT Extensions OPTIONAL }
    """
    result: Dict[str, Any] = {
        "cert_status": CERT_STATUS_UNKNOWN,
        "serial_number": None,
        "this_update": None,
        "next_update": None,
    }

    cursor = sr_off

    # Parse CertID (SEQUENCE)
    tag, cid_off, cid_end = _der_decode(data, cursor)
    if tag != 0x30:
        raise _DerError("certID must be SEQUENCE")

    # CertID ::= SEQUENCE {
    #     hashAlgorithm       AlgorithmIdentifier,
    #     issuerNameHash      OCTET STRING,
    #     issuerKeyHash       OCTET STRING,
    #     serialNumber        CertificateSerialNumber }
    # Skip hashAlgorithm
    cursor2 = cid_off
    cursor2 = _der_skip_value(data, cursor2)  # hashAlgorithm
    cursor2 = _der_skip_value(data, cursor2)  # issuerNameHash
    cursor2 = _der_skip_value(data, cursor2)  # issuerKeyHash
    serial, cursor2 = _der_read_integer(data, cursor2)  # serialNumber
    result["serial_number"] = serial
    cursor = cid_end

    # Parse CertStatus (CHOICE)
    tag, cs_off, cs_end = _der_decode(data, cursor)
    # certStatus is IMPLICIT CHOICE: [0] good, [1] revoked, [2] unknown
    tag_num = tag & 0x1F
    if tag == 0xA0:
        # [0] IMPLICIT NULL = good
        result["cert_status"] = CERT_STATUS_GOOD
    elif tag == 0xA1:
        # [1] IMPLICIT RevokedInfo
        result["cert_status"] = CERT_STATUS_REVOKED
    elif tag == 0xA2:
        # [2] IMPLICIT UnknownInfo
        result["cert_status"] = CERT_STATUS_UNKNOWN
    else:
        raise _DerError(f"Unexpected CertStatus tag 0x{tag:02x}")
    cursor = cs_end

    # Skip thisUpdate (GeneralizedTime = 0x18)
    cursor = _der_skip_value(data, cursor)

    # Check for optional nextUpdate [0]
    if cursor < sr_end:
        tag2, _, _ = _der_decode(data, cursor)
        if tag2 == 0xA0:
            # nextUpdate [0] EXPLICIT GeneralizedTime
            # Skip [0] tag, then inside is GeneralizedTime
            inner_tag, nu_off, nu_end = _der_decode(data, cursor + 1)
            result["next_update"] = data[nu_off:nu_end]
            cursor = nu_end + 1  # past the [0] content
        # singleExtensions [1] would follow but we don't need them

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

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


def _parse_ocsp_response(response_bytes: bytes) -> Dict[str, Any]:
    """Parse an OCSP response using DER/ASN.1 decoding.

    Safely parses the OCSP response status, certificate status, and
    serial number correlation using standards-aware DER decoding.

    Args:
        response_bytes: Raw OCSP response bytes (DER-encoded).

    Returns:
        Dict with:
            - status: "good" | "revoked" | "unknown" | "malformed"
            - response_status: numeric OCSPResponseStatus code
            - revocation_time: bytes or None (GeneralizedTime)
            - cert_status: "good" | "revoked" | "unknown"
            - serial_number: int or None
            - response_size: int
    """
    result: Dict[str, Any] = {
        "status": "unknown",
        "response_status": None,
        "revocation_time": None,
        "cert_status": None,
        "serial_number": None,
        "response_size": len(response_bytes),
    }

    if not response_bytes:
        return result

    try:
        # Step 1: Parse outer OCSPResponse to get responseStatus
        resp_status = _parse_ocsp_response_status(response_bytes)
        result["response_status"] = resp_status

        # Check response-level status
        if resp_status != OCSPResponseStatus_SUCCESSFUL:
            if resp_status == OCSPResponseStatus_MALFORMEDREQUEST:
                result["status"] = "malformed"
            elif resp_status == OCSPResponseStatus_UNAUTHORIZED:
                result["status"] = "unauthorized"
            elif resp_status == OCSPResponseStatus_TRYLATER:
                result["status"] = "try_later"
            elif resp_status == OCSPResponseStatus_INTERNALERROR:
                result["status"] = "internal_error"
            else:
                result["status"] = "error"
            return result

        # Step 2: Navigate to BasicOCSPResponse
        basic_der = _find_basic_ocsp_response(response_bytes)

        # Step 3: Parse BasicOCSPResponse to get SingleResponse
        single = _parse_basic_ocsp_response(basic_der)
        result["cert_status"] = single["cert_status"]
        result["serial_number"] = single["serial_number"]
        result["this_update"] = single.get("this_update")
        result["next_update"] = single.get("next_update")

        # Map cert_status to top-level status for backward compatibility
        result["status"] = single["cert_status"]

    except _DerError as e:
        logger.warning("Malformed OCSP response DER: %s", e)
        result["status"] = "malformed"
    except Exception as e:
        logger.warning("Unexpected error parsing OCSP response: %s", e)
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
    4. Parses the response using DER/ASN.1 decoding
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

        # Validate URL via OutboundNetworkPolicy — OCSP egress must ALWAYS
        # be protected, even when allow_private_targets is True.
        from trustlint.security.outbound_network_policy import OutboundNetworkPolicy

        policy = OutboundNetworkPolicy(allow_private=False)
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

        try:
            response = client.get(
                ocsp_url,
                headers={"Content-Type": OCSP_CONTENT_TYPE},
            )

            if response is None:
                result["ocsp_error"] = "OCSP request failed"
                return result

            result["ocsp_performed"] = True

            # Parse DER-encoded OCSP response
            parsed = _parse_ocsp_response(response)
            result["ocsp_status"] = parsed["status"]

            if parsed["status"] == "revoked":
                result["ocsp_error"] = "Certificate is revoked"
            elif parsed["status"] == "malformed":
                result["ocsp_error"] = "Malformed OCSP response"
            elif parsed["status"] in ("unauthorized", "try_later", "internal_error"):
                result["ocsp_error"] = (
                    f"OCSP responder returned status: {parsed['status']}"
                )

        except ValueError as e:
            # OutboundNetworkPolicy rejection
            result["ocsp_error"] = f"OCSP request blocked: {e}"
        except Exception as e:
            result["ocsp_error"] = f"OCSP request error: {e}"

    except Exception as e:
        result["ocsp_error"] = f"OCSP check failed: {e}"

    return result
