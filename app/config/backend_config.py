"""Backend connection settings, read from `BACKEND_*` environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendConfig(BaseSettings):
    """Settings for connecting to the backend.

    Each field is read from the environment variable `BACKEND_<FIELD NAME>`, such as
    `BACKEND_BASE_URL`, or else from the `.env` file in the working directory.
    """

    model_config = SettingsConfigDict(
        env_prefix="BACKEND_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str = Field(
        default="http://127.0.0.1:8000",
        min_length=1,
        description="Backend base URL",
    )
    ip_address_report_endpoint: str = Field(
        default="/api/v1/ip_address_report",
        min_length=1,
        description="Backend endpoint for IP address reports",
    )
    timeout_seconds: float = Field(
        default=60,
        gt=0,
        le=180,
        description="Timeout in seconds for backend requests",
    )


backend_config = BackendConfig()
