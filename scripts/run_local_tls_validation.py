"""TLS validation wrapper for backward compatibility.

The real implementation is in trustlint.infrastructure.tls_probe.
This file maintains backward compatibility for scripts importing run_local_tls_validation.
"""

from trustlint.infrastructure.tls_probe import *
from trustlint.infrastructure.tls_probe import (
    _attempt_tls_handshake,
    _resolve_domain,
    _classify_ssl_error,
    _create_tls_context,
)
