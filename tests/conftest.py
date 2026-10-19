"""Keep the test suite isolated from external observability services."""

import pytest


@pytest.fixture(autouse=True)
def disable_external_telemetry(monkeypatch):
    monkeypatch.setenv("LANGFUSE_ENABLED", "false")
