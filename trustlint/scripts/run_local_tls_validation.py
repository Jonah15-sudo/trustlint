"""TLS validation wrapper for backward compatibility.

The real implementation is in trustlint.infrastructure.tls_probe.
This file maintains backward compatibility for scripts importing run_local_tls_validation.
"""

from trustlint.infrastructure.tls_probe import (
    probe_domain,
    _attempt_tls_handshake,
    _resolve_domain,
    _classify_ssl_error,
    _create_tls_context,
    PROBE_TIMEOUT,
    RATE_LIMIT_SECONDS,
    DEFAULT_PORT,
    REPORT_DIR,
    CLASSIFICATION,
    CLASSIFICATION_ORDER,
)

from trustlint.infrastructure.tls_compat import (
    _determine_chain_subtype,
    _build_mixed_report,
    logger,
)

__all__ = [
    "probe_domain",
    "_attempt_tls_handshake",
    "_resolve_domain",
    "_classify_ssl_error",
    "_create_tls_context",
    "_determine_chain_subtype",
    "_build_mixed_report",
    "logger",
    "PROBE_TIMEOUT",
    "RATE_LIMIT_SECONDS",
    "DEFAULT_PORT",
    "REPORT_DIR",
    "CLASSIFICATION",
    "CLASSIFICATION_ORDER",
]
