"""Target scanning policy for TLS analysis.

Controls which IP addresses and domains are permitted for TLS probing.
Prevents accidental scanning of internal/private infrastructure.

Default policy (safe for public-facing products):
- Rejects loopback addresses
- Rejects RFC1918 private ranges
- Rejects link-local addresses
- Rejects multicast/reserved ranges
- Rejects cloud metadata endpoints

Opt-in for internal scanning:
    policy = TargetScanPolicy(allow_private=True)

Usage:
    policy = TargetScanPolicy()
    ip = policy.validate_and_resolve("example.com")
    # Raises ValueError for private IPs
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Optional, Set

logger = logging.getLogger(__name__)


class TargetScanPolicy:
    """Controls which targets are permitted for TLS scanning.

    Validates both hostnames (via DNS resolution) and IP addresses
    against a set of network restrictions.
    """

    def __init__(
        self,
        allow_private: bool = False,
        allow_loopback: bool = False,
        allow_link_local: bool = False,
        allow_cloud_metadata: bool = False,
        additional_blocked_hosts: Optional[Set[str]] = None,
    ) -> None:
        self.allow_private = allow_private
        self.allow_loopback = allow_loopback
        self.allow_link_local = allow_link_local
        self.allow_cloud_metadata = allow_cloud_metadata
        self._blocked_hosts = {
            "169.254.169.254",
            "metadata.google.internal",
            "localhost",
        }
        if additional_blocked_hosts:
            self._blocked_hosts.update(additional_blocked_hosts)

    def validate_target(self, target: str) -> str:
        """Validate a target domain/IP and return the resolved IP.

        Args:
            target: Domain name or IP address to validate.

        Returns:
            Resolved IP address string.

        Raises:
            ValueError: If target resolves to a restricted IP range.
            socket.gaierror: If DNS resolution fails.
        """
        target = target.strip().lower()

        # Check blocked hosts
        if target in self._blocked_hosts:
            raise ValueError(
                f"Target '{target}' is a known metadata/reserved endpoint "
                "and must not be scanned"
            )

        # Try parsing as IP address directly
        try:
            ip = ipaddress.ip_address(target)
            self._validate_ip(ip, target)
            return str(ip)
        except ValueError:
            # Not a raw IP, resolve via DNS
            pass

        # DNS resolution
        resolved_ip = self._resolve_domain(target)
        resolved_addr = ipaddress.ip_address(resolved_ip)
        self._validate_ip(resolved_addr, target)

        return resolved_ip

    def validate_ip(self, ip_str: str) -> None:
        """Validate an IP address string directly."""
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError(f"Invalid IP address: {ip_str}")
        self._validate_ip(ip, ip_str)

    def _validate_ip(self, ip: ipaddress.IPAddress, label: str) -> None:
        """Check if an IP address is in a restricted range."""
        # Explicit check for 0.0.0.0 (may not be classified as reserved in all Python versions)
        if str(ip) == "0.0.0.0":
            raise ValueError(
                f"Target '{label}' resolves to unspecified address {ip}."
            )

        # Check reserved ranges
        if ip.is_reserved:
            raise ValueError(
                f"Target '{label}' resolves to reserved address {ip}."
            )

        if not self.allow_loopback:
            if ip.is_loopback:
                raise ValueError(
                    f"Target '{label}' resolves to loopback address {ip}. "
                    "Use allow_loopback=True to override."
                )

        if not self.allow_link_local:
            if ip.is_link_local:
                raise ValueError(
                    f"Target '{label}' resolves to link-local address {ip}. "
                    "Use allow_link_local=True to override."
                )

        if not self.allow_private:
            if ip.is_private:
                raise ValueError(
                    f"Target '{label}' resolves to private address {ip}. "
                    "Use allow_private=True for internal scanning."
                )

        if ip.is_multicast:
            raise ValueError(
                f"Target '{label}' resolves to multicast address {ip}."
            )

    def _resolve_domain(self, domain: str) -> str:
        """Resolve domain to an IPv4 address.

        Returns:
            IPv4 address string.

        Raises:
            ValueError: If resolution fails.
        """
        try:
            addrs = socket.getaddrinfo(
                domain, 443, socket.AF_INET, socket.SOCK_STREAM
            )
            if addrs:
                return addrs[0][4][0]
            raise ValueError(f"No IPv4 records found for '{domain}'")
        except socket.gaierror as e:
            raise ValueError(f"DNS resolution failed for '{domain}': {e}")
