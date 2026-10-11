"""Set the backend environment variables to test values before `app` is imported."""

import os

# Must run before `app` is imported: backend_config is created at import time.
# Plain assignment (not setdefault) so values from .env or the shell never leak into tests;
# env vars take precedence over .env in pydantic-settings.
os.environ["BACKEND_BASE_URL"] = "http://backend.test"
os.environ["BACKEND_IP_ADDRESS_REPORT_ENDPOINT"] = "/api/v1/ip_address_report"
os.environ["BACKEND_TIMEOUT_SECONDS"] = "5"
