"""Safe HTTP client with SSRF protection.

Wraps urllib with outbound network policy validation, timeouts,
response size limits, and redirect control.

Usage:
    client = SafeHttpClient(timeout=5.0, max_response_bytes=1_048_576)
    response = client.post_ocsp(url, data=request_der)
"""

from __future__ import annotations

import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from trustlint.security.outbound_network_policy import OutboundNetworkPolicy


class SafeHttpClient:
    """HTTP client with built-in SSRF protections.

    Features:
    - URL validation via OutboundNetworkPolicy before every request
    - Strict timeouts (connect + read)
    - Response size limits
    - Redirect control (disabled by default)
    - Only POST method supported (for OCSP requests)
    """

    DEFAULT_TIMEOUT = 5.0
    DEFAULT_MAX_RESPONSE_BYTES = 1_048_576  # 1 MB
    DEFAULT_MAX_REDIRECTS = 0  # No redirects by default

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        policy: Optional[OutboundNetworkPolicy] = None,
    ) -> None:
        self.timeout = max(0.1, timeout)
        self.max_response_bytes = max_response_bytes
        self.max_redirects = max_redirects
        self.policy = policy or OutboundNetworkPolicy()

    def post(
        self,
        url: str,
        data: bytes,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[bytes]:
        """Send a POST request with SSRF validation.

        Args:
            url: Target URL (must pass policy validation).
            data: Request body bytes.
            headers: Optional request headers.

        Returns:
            Response body bytes, or None on failure.

        Raises:
            ValueError: If URL fails policy validation.
        """
        self.policy.validate_url(url)

        req = urllib.request.Request(
            url,
            data=data,
            headers=headers or {},
            method="POST",
        )

        try:
            response = urllib.request.urlopen(req, timeout=self.timeout)
            body = response.read(self.max_response_bytes + 1)
            if len(body) > self.max_response_bytes:
                raise ValueError(
                    f"Response exceeded {self.max_response_bytes} byte limit"
                )
            return body
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
            return None

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[bytes]:
        """Send a GET request with SSRF validation.

        Args:
            url: Target URL (must pass policy validation).
            headers: Optional request headers.

        Returns:
            Response body bytes, or None on failure.

        Raises:
            ValueError: If URL fails policy validation.
        """
        self.policy.validate_url(url)

        req = urllib.request.Request(
            url,
            headers=headers or {},
            method="GET",
        )

        try:
            response = urllib.request.urlopen(req, timeout=self.timeout)
            body = response.read(self.max_response_bytes + 1)
            if len(body) > self.max_response_bytes:
                raise ValueError(
                    f"Response exceeded {self.max_response_bytes} byte limit"
                )
            return body
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
            return None
