from __future__ import annotations

"""Error code definitions for TrustLint.

All pipeline errors are mapped to unique string codes for machine-readable
error handling. Each code includes a human-readable description.
"""

from enum import Enum
from typing import Dict, Optional, Type


class ErrorCode(str, Enum):
    """Structured error codes for pipeline errors."""

    # DNS errors
    DNS_RESOLUTION_FAILED = "E1001"
    DNS_NO_RECORDS = "E1002"

    # Connection errors
    CONNECTION_REFUSED = "E2001"
    CONNECTION_RESET = "E2002"
    CONNECTION_TIMEOUT = "E2003"
    CONNECTION_ERROR = "E2004"

    # TLS errors
    TLS_HANDSHAKE_FAILED = "E3001"
    TLS_CERT_EXPIRED = "E3002"
    TLS_CERT_REVOKED = "E3003"
    TLS_CERT_SELF_SIGNED = "E3004"
    TLS_CERT_UNTRUSTED = "E3005"
    TLS_CERT_INCOMPLETE_CHAIN = "E3006"
    TLS_WRONG_HOST = "E3007"
    TLS_WEAK_CIPHER = "E3008"
    TLS_WEAK_SIGNATURE = "E3009"
    TLS_DEPRECATED_VERSION = "E3010"
    TLS_COMPRESSION_ENABLED = "E3011"
    TLS_STATIC_RSA = "E3012"
    TLS_WILDCARD_CERT = "E3013"
    TLS_MISSING_OCSP = "E3014"
    TLS_OCSP_UNREACHABLE = "E3015"
    TLS_UNKNOWN_ERROR = "E3016"

    # OCSP errors
    OCSP_REQUEST_FAILED = "E4001"
    OCSP_RESPONSE_INVALID = "E4002"
    OCSP_STAPLING_UNAVAILABLE = "E4003"

    # Pipeline errors
    PIPELINE_INIT_FAILED = "E5001"
    PIPELINE_PROCESS_FAILED = "E5002"
    PIPELINE_INGEST_FAILED = "E5003"

    # Validation errors
    INVALID_DOMAIN = "E6001"
    INVALID_INPUT = "E6002"

    # System errors
    PYTHON_VERSION_UNSUPPORTED = "E7001"
    SSL_MODULE_UNAVAILABLE = "E7002"
    CONFIG_MISSING = "E7003"
    FILE_NOT_FOUND = "E7004"
    FILE_WRITE_FAILED = "E7005"

    # Unknown
    UNKNOWN_ERROR = "E9999"

# Mapping from ErrorCode to human-readable description
ERROR_CODE_MAP: Dict[ErrorCode, str] = {
    ErrorCode.DNS_RESOLUTION_FAILED: "DNS resolution failed for domain",
    ErrorCode.DNS_NO_RECORDS: "No DNS records found for domain",
    ErrorCode.CONNECTION_REFUSED: "Server refused connection",
    ErrorCode.CONNECTION_RESET: "Connection was reset by server",
    ErrorCode.CONNECTION_TIMEOUT: "Connection timed out",
    ErrorCode.CONNECTION_ERROR: "Connection error occurred",
    ErrorCode.TLS_HANDSHAKE_FAILED: "TLS handshake failed",
    ErrorCode.TLS_CERT_EXPIRED: "Certificate has expired",
    ErrorCode.TLS_CERT_REVOKED: "Certificate has been revoked",
    ErrorCode.TLS_CERT_SELF_SIGNED: "Certificate is self-signed",
    ErrorCode.TLS_CERT_UNTRUSTED: "Certificate chain is not trusted",
    ErrorCode.TLS_CERT_INCOMPLETE_CHAIN: "Certificate chain is incomplete",
    ErrorCode.TLS_WRONG_HOST: "Certificate does not match hostname",
    ErrorCode.TLS_WEAK_CIPHER: "Weak cipher suite negotiated",
    ErrorCode.TLS_WEAK_SIGNATURE: "Weak signature algorithm",
    ErrorCode.TLS_DEPRECATED_VERSION: "Deprecated TLS version",
    ErrorCode.TLS_COMPRESSION_ENABLED: "TLS compression enabled",
    ErrorCode.TLS_STATIC_RSA: "Static RSA key exchange",
    ErrorCode.TLS_WILDCARD_CERT: "Wildcard certificate",
    ErrorCode.TLS_MISSING_OCSP: "OCSP staple not provided",
    ErrorCode.TLS_OCSP_UNREACHABLE: "OCSP responder unreachable",
    ErrorCode.TLS_UNKNOWN_ERROR: "Unknown TLS error",
    ErrorCode.OCSP_REQUEST_FAILED: "OCSP request failed",
    ErrorCode.OCSP_RESPONSE_INVALID: "OCSP response is invalid",
    ErrorCode.OCSP_STAPLING_UNAVAILABLE: "OCSP stapling not available",
    ErrorCode.PIPELINE_INIT_FAILED: "Pipeline initialization failed",
    ErrorCode.PIPELINE_PROCESS_FAILED: "Pipeline processing failed",
    ErrorCode.PIPELINE_INGEST_FAILED: "Pipeline ingestion failed",
    ErrorCode.INVALID_DOMAIN: "Invalid domain format",
    ErrorCode.INVALID_INPUT: "Invalid input",
    ErrorCode.PYTHON_VERSION_UNSUPPORTED: "Python version not supported",
    ErrorCode.SSL_MODULE_UNAVAILABLE: "SSL module unavailable",
    ErrorCode.CONFIG_MISSING: "Configuration missing",
    ErrorCode.FILE_NOT_FOUND: "File not found",
    ErrorCode.FILE_WRITE_FAILED: "File write failed",
    ErrorCode.UNKNOWN_ERROR: "Unknown error",
}

# Mapping from exception type to ErrorCode
_EXCEPTION_CODE_MAP: Dict[Type[Exception], ErrorCode] = {
    ConnectionRefusedError: ErrorCode.CONNECTION_REFUSED,
    ConnectionResetError: ErrorCode.CONNECTION_RESET,
    TimeoutError: ErrorCode.CONNECTION_TIMEOUT,
    OSError: ErrorCode.CONNECTION_ERROR,
    FileNotFoundError: ErrorCode.FILE_NOT_FOUND,
    PermissionError: ErrorCode.FILE_WRITE_FAILED,
    ImportError: ErrorCode.SSL_MODULE_UNAVAILABLE,
    ValueError: ErrorCode.INVALID_INPUT,
    KeyError: ErrorCode.INVALID_INPUT,
}


def get_error_code(exc: Exception) -> ErrorCode:
    """Get the ErrorCode for an exception.

    Maps known exception types to structured error codes.
    Falls back to UNKNOWN_ERROR for unrecognized exceptions.
    """
    exc_type = type(exc)

    # Check for SSL-specific errors
    import ssl
    if isinstance(exc, ssl.SSLCertVerificationError):
        msg = str(exc).lower()
        if "expired" in msg:
            return ErrorCode.TLS_CERT_EXPIRED
        if "revoked" in msg:
            return ErrorCode.TLS_CERT_REVOKED
        if "self-signed" in msg:
            return ErrorCode.TLS_CERT_SELF_SIGNED
        if "untrusted" in msg or "unable to get local issuer" in msg:
            return ErrorCode.TLS_CERT_UNTRUSTED
        if "hostname mismatch" in msg or "doesn't match" in msg:
            return ErrorCode.TLS_WRONG_HOST
        return ErrorCode.TLS_HANDSHAKE_FAILED

    if isinstance(exc, ssl.SSLError):
        return ErrorCode.TLS_HANDSHAKE_FAILED

    # Check for socket errors
    import socket
    if isinstance(exc, socket.timeout):
        return ErrorCode.CONNECTION_TIMEOUT
    if isinstance(exc, socket.gaierror):
        return ErrorCode.DNS_RESOLUTION_FAILED

    # Direct exception type mapping
    for exc_type_check, code in _EXCEPTION_CODE_MAP.items():
        if isinstance(exc, exc_type_check):
            return code

    return ErrorCode.UNKNOWN_ERROR


def format_error_message(domain: str, code: ErrorCode, detail: str) -> str:
    """Format an error message with structured code prefix.

    Example: "[E2003] example.com: Connection timed out"
    """
    return f"[{code.value}] {domain}: {detail}"


def format_error_for_log(domain: str, exc: Exception) -> str:
    """Format an exception for logging with error code.

    Example: "[E2003] example.com: Connection timed out: [Errno 110] Connection timed out"
    """
    code = get_error_code(exc)
    return format_error_message(domain, code, str(exc))
