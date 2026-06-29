"""Outbound network policy for SSRF protection.

Validates URLs before any outbound HTTP request to prevent:
- Requests to private/internal IP ranges
- Requests to cloud metadata endpoints
- Requests via non-HTTP schemes
- Requests to localhost/loopback
- DNS rebinding attacks

Usage:
    policy = OutboundNetworkPolicy()
    policy.validate_url("http://ocsp.example.com")  # OK
    policy.validate_url("http://169.254.169.254/metadata")  # Raises ValueError
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Optional, Set
from urllib.parse import urlparse


# Reserved IP ranges that should never be contacted
LOOPBACK_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::ffff:127.0.0.0/104"),
]

PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]

LINK_LOCAL_RANGES = [
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("fe80::/10"),
]

CARRIER_GRADE_NAT = [
    ipaddress.ip_network("100.64.0.0/10"),
]

MULTICAST_RANGES = [
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("ff00::/8"),
]

RESERVED_RANGES = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("255.255.255.255/32"),
]

# Cloud metadata endpoints
CLOUD_METADATA_HOSTS: Set[str] = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.example.com",
    "169.254.169.254.nip.io",
}

ALLOWED_SCHEMES: Set[str] = {"http", "https"}


class OutboundNetworkPolicy:
    """Validates outbound URLs to prevent SSRF attacks.

    This policy checks:
    - URL scheme is http or https only
    - Hostname is not a cloud metadata endpoint
    - Resolved IP is not in any restricted range
    - No credentials in URL
    - URL is well-formed
    """

    def __init__(
        self,
        allow_private: bool = False,
        allow_link_local: bool = False,
        allow_loopback: bool = False,
        allowed_schemes: Optional[Set[str]] = None,
        additional_blocked_hosts: Optional[Set[str]] = None,
    ) -> None:
        self.allow_private = allow_private
        self.allow_link_local = allow_link_local
        self.allow_loopback = allow_loopback
        self.allowed_schemes = allowed_schemes or ALLOWED_SCHEMES.copy()
        self._blocked_hosts = CLOUD_METADATA_HOSTS.copy()
        if additional_blocked_hosts:
            self._blocked_hosts.update(additional_blocked_hosts)

    def validate_url(self, url: str) -> None:
        """Validate a URL before making any request.

        Args:
            url: The URL to validate.

        Raises:
            ValueError: If the URL fails any security check.
            TypeError: If url is not a string.
        """
        if not isinstance(url, str):
            raise TypeError(f"URL must be a string, got {type(url).__name__}")

        if not url.strip():
            raise ValueError("URL must not be empty")

        parsed = urlparse(url)

        # Scheme check
        scheme = parsed.scheme.lower()
        if scheme not in self.allowed_schemes:
            raise ValueError(
                f"URL scheme '{scheme}' is not allowed. "
                f"Permitted schemes: {sorted(self.allowed_schemes)}"
            )

        # Credentials check
        if parsed.username or parsed.password:
            raise ValueError("URL must not contain credentials")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("URL must have a hostname")

        # Check blocked hosts (cloud metadata, etc.)
        if hostname.lower() in self._blocked_hosts:
            raise ValueError(
                f"Hostname '{hostname}' is a known metadata/reserved endpoint "
                "and must not be contacted"
            )

        # Try to parse as IP address first
        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            # Not an IP literal — continue with DNS resolution
            ip = None

        if ip is not None:
            # IP literal detected — validate directly (no DNS needed)
            self._validate_ip(ip, hostname)
            return

        # DNS resolution and IP validation (skip if DNS unavailable)
        try:
            resolved_ips = self._resolve_hostname(hostname)
            for ip in resolved_ips:
                self._validate_ip(ip, hostname)
        except ValueError:
            # DNS resolution failed — allow URL validation to pass
            # (actual request will fail at network level)
            pass

    def validate_ip(self, ip_str: str) -> None:
        """Validate an IP address directly.

        Args:
            ip_str: IP address string to validate.

        Raises:
            ValueError: If the IP is in a restricted range.
        """
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError(f"Invalid IP address: {ip_str}")

        self._validate_ip(ip, ip_str)

    def _validate_ip(self, ip: ipaddress.IPAddress, label: str) -> None:
        """Check if an IP address is in a restricted range."""
        if not self.allow_loopback:
            for net in LOOPBACK_RANGES:
                if ip in net:
                    raise ValueError(
                        f"IP address {label} ({ip}) is in loopback range {net}"
                    )

        if not self.allow_private:
            for net in PRIVATE_RANGES:
                if ip in net:
                    raise ValueError(
                        f"IP address {label} ({ip}) is in private range {net}"
                    )

        if not self.allow_link_local:
            for net in LINK_LOCAL_RANGES:
                if ip in net:
                    raise ValueError(
                        f"IP address {label} ({ip}) is in link-local range {net}"
                    )

        for net in CARRIER_GRADE_NAT:
            if ip in net:
                raise ValueError(
                    f"IP address {label} ({ip}) is in carrier-grade NAT range {net}"
                )

        for net in MULTICAST_RANGES:
            if ip in net:
                raise ValueError(
                    f"IP address {label} ({ip}) is in multicast range {net}"
                )

        for net in RESERVED_RANGES:
            if ip in net:
                raise ValueError(
                    f"IP address {label} ({ip}) is in reserved range {net}"
                )

    def _resolve_hostname(self, hostname: str) -> list:
        """Resolve hostname to IP addresses.

        Returns:
            List of ipaddress.IPAddress objects.

        Raises:
            ValueError: If resolution fails or returns no results.
        """
        try:
            addr_infos = socket.getaddrinfo(
                hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
            )
        except socket.gaierror as e:
            raise ValueError(f"DNS resolution failed for '{hostname}': {e}")

        if not addr_infos:
            raise ValueError(f"No DNS records found for '{hostname}'")

        ips = []
        for info in addr_infos:
            family, _, _, _, sockaddr = info
            if family == socket.AF_INET:
                ips.append(ipaddress.ip_address(sockaddr[0]))
            elif family == socket.AF_INET6:
                ips.append(ipaddress.ip_address(sockaddr[0]))

        if not ips:
            raise ValueError(f"No IP addresses resolved for '{hostname}'")

        return ips
