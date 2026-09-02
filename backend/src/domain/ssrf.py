"""SSRF host validation — shared by URL-fetching call sites.

Rejects private/loopback/link-local/reserved/unspecified/multicast hosts so
user-influenced URLs can never reach internal infrastructure (RFC1918,
cloud metadata 169.254.169.254, localhost services).

Transport-agnostic: raises ``ValueError`` on blocked hosts so each caller
decides how to surface the failure (HTTP error vs. soft-failure message).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def resolve_host_ip(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Resolve a hostname to an IP address, raising ``ValueError`` on failure."""
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        try:
            return ipaddress.ip_address(socket.gethostbyname(hostname))
        except OSError:
            raise ValueError(f"无法解析链接域名: {hostname}") from None


def is_private_host(host_ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True when the IP must never be reachable from a server-side fetch."""
    return (
        host_ip.is_private
        or host_ip.is_loopback
        or host_ip.is_link_local
        or host_ip.is_reserved
        or host_ip.is_unspecified
        or host_ip.is_multicast
    )


def validate_public_host(hostname: str) -> None:
    """Reject private/loopback/link-local/reserved hosts (every redirect hop).

    Raises ``ValueError`` with a user-facing Chinese message when the host is
    blocked or unresolvable.
    """
    host_ip = resolve_host_ip(hostname)
    if is_private_host(host_ip):
        raise ValueError("不允许连接内网地址")


def validate_public_url(url: str) -> None:
    """Reject non-http(s) schemes and private hosts in a URL.

    Raises ``ValueError`` on blocked schemes or hosts.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("仅支持 http/https 链接")
    validate_public_host(parsed.hostname or "")
