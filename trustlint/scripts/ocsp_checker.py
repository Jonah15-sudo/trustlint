"""OCSP checker wrapper for backward compatibility.

The real implementation is in trustlint.infrastructure.ocsp.client.
This file maintains backward compatibility for scripts importing ocsp_checker.
"""

from trustlint.infrastructure.ocsp.client import check_ocsp

__all__ = ["check_ocsp"]
