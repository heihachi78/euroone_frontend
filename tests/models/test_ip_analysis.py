"""Tests for the `IpAnalysis` model."""

import pytest
from pydantic import ValidationError

from app.models.ip_analysis import IpAnalysis


@pytest.mark.parametrize("ip", ["8.8.8.8", "2001:4860:4860::8888"])
def test_parses_backend_response(ip: str) -> None:
    """A complete response with an IPv4 or IPv6 address is parsed."""
    analysis = IpAnalysis.model_validate({"ip": ip, "summary": "**Google DNS**"})

    assert str(analysis.ip) == ip
    assert analysis.summary == "**Google DNS**"


@pytest.mark.parametrize(
    "payload",
    [
        {"ip": "8.8.8.8"},
        {"summary": "**Google DNS**"},
        {"ip": "not an ip", "summary": "**Google DNS**"},
    ],
)
def test_rejects_incomplete_or_invalid_response(payload: dict[str, str]) -> None:
    """A response with a missing field or an invalid IP address is rejected."""
    with pytest.raises(ValidationError):
        IpAnalysis.model_validate(payload)
