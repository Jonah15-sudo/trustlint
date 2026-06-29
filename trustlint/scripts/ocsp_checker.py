"""OCSP checker wrapper for backward compatibility.

The real implementation is in trustlint.infrastructure.tls_probe.
This file maintains backward compatibility for scripts importing ocsp_checker.
"""

from trustlint.infrastructure.tls_probe import check_ocsp
