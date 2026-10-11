"""Tests for `BackendConfig` and the `backend_config` instance."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.config.backend_config import BackendConfig, backend_config


def test_config_uses_test_values_not_the_real_env_file() -> None:
    """Guard for the test setup in conftest.py: tests never read the real .env or shell values."""
    assert backend_config.base_url == "http://backend.test"
    assert backend_config.ip_address_report_endpoint == "/api/v1/ip_address_report"
    assert backend_config.timeout_seconds == 5


def test_defaults_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without environment variables or a `.env` file, the defaults are used."""
    monkeypatch.delenv("BACKEND_BASE_URL")
    monkeypatch.delenv("BACKEND_IP_ADDRESS_REPORT_ENDPOINT")
    monkeypatch.delenv("BACKEND_TIMEOUT_SECONDS")

    config = BackendConfig(_env_file=None)  # pyright: ignore[reportCallIssue]

    assert config.base_url == "http://127.0.0.1:8000"
    assert config.ip_address_report_endpoint == "/api/v1/ip_address_report"
    assert config.timeout_seconds == 60


@pytest.mark.parametrize(
    "values",
    [
        {"base_url": ""},
        {"ip_address_report_endpoint": ""},
        {"timeout_seconds": 0},
        {"timeout_seconds": 181},
    ],
)
def test_rejects_invalid_values(values: dict[str, Any]) -> None:
    """Empty URLs and timeouts outside (0, 180] seconds are rejected."""
    with pytest.raises(ValidationError):
        BackendConfig(**values)
