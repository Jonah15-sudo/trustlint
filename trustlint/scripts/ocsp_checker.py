"""OCSP checker wrapper for backward compatibility.

The real implementation is in trustlint.infrastructure.ocsp.client.
This file maintains backward compatibility for scripts importing ocsp_checker.
"""

from trustlint.infrastructure.ocsp.client import (
    check_ocsp,
    _extract_ocsp_urls,
    _parse_ocsp_response,
    OCSP_TIMEOUT,
    OCSP_MAX_RESPONSE_BYTES,
)

from trustlint.infrastructure.ocsp.compat import (
    check_ocsp_stapled,
    _get_issuer_spki,
    _parse_tbs,
)

__all__ = [
    "check_ocsp",
    "check_ocsp_stapled",
    "_extract_ocsp_urls",
    "_parse_ocsp_response",
    "_get_issuer_spki",
    "_parse_tbs",
    "OCSP_TIMEOUT",
    "OCSP_MAX_RESPONSE_BYTES",
]
