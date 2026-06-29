"""TLS validation wrapper for backward compatibility.

The real implementation is in trustlint.infrastructure.tls_probe.
This file maintains backward compatibility for scripts importing run_local_tls_validation.
"""

from trustlint.infrastructure.tls_probe import *
