"""OCSP checking infrastructure.

OCSP (Online Certificate Status Protocol) checking and validation.
The real implementation is in trustlint.infrastructure.ocsp.client.
"""

from trustlint.infrastructure.ocsp.client import (
    check_ocsp,
    _extract_ocsp_urls,
    _parse_ocsp_response,
    OCSP_TIMEOUT,
    OCSP_MAX_RESPONSE_BYTES,
)

__all__ = [
    "check_ocsp",
    "_extract_ocsp_urls",
    "_parse_ocsp_response",
    "OCSP_TIMEOUT",
    "OCSP_MAX_RESPONSE_BYTES",
]
