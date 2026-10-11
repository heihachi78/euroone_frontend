"""Tests for the `Ip` model and `ip_error`."""

import pytest

from app.models.ip import EMPTY_IP_MESSAGE, Ip, ip_error

INVALID_FORMAT = "value is not a valid IPv4 or IPv6 address"
NOT_PUBLIC = "IP address must be a public unicast address"


@pytest.mark.parametrize("value", ["8.8.8.8", " 8.8.8.8 ", "2001:4860:4860::8888"])
def test_ip_error_accepts_public_addresses(value: str) -> None:
    """Public IPv4 and IPv6 addresses are valid, even with surrounding whitespace."""
    assert ip_error(value) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", EMPTY_IP_MESSAGE),
        ("   ", EMPTY_IP_MESSAGE),
        ("1.2.3", INVALID_FORMAT),
        ("8.8.8.8.8", INVALID_FORMAT),
        ("hello", INVALID_FORMAT),
        ("192.168.1.1", NOT_PUBLIC),
        ("127.0.0.1", NOT_PUBLIC),
        ("::1", NOT_PUBLIC),
        ("224.0.0.1", NOT_PUBLIC),
        ("fe80::1%eth0", "IP address must not contain a scope ID"),
    ],
)
def test_ip_error_rejects_invalid_addresses(value: str, expected: str) -> None:
    """Empty, malformed, non-public and scoped addresses get the matching message."""
    assert ip_error(value) == expected


def test_ip_maps_ipv4_mapped_ipv6_to_ipv4() -> None:
    """An IPv4-mapped IPv6 address is stored as its IPv4 address."""
    assert str(Ip(ip="::ffff:8.8.8.8").ip) == "8.8.8.8"  # pyright: ignore[reportArgumentType]
