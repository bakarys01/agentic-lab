import pytest

from a2a_clients import client_utils
from tools import delegation


@pytest.mark.parametrize(
    "name,port",
    [
        ("policy", 9999),
        ("research", 9998),
        ("healthcare_provider", 9997),
    ],
)
def test_specialist_url_uses_configured_port_and_public_url(
    monkeypatch, name, port
):
    prefix = name.upper()
    monkeypatch.delenv(f"{prefix}_AGENT_PUBLIC_URL", raising=False)

    assert client_utils.get_agent_url(name) == f"http://127.0.0.1:{port}"

    monkeypatch.setenv(
        f"{prefix}_AGENT_PUBLIC_URL",
        "http://localhost:23456/",
    )
    assert client_utils.get_agent_url(name) == "http://localhost:23456"

@pytest.mark.parametrize("name", ["policy", "research", "healthcare_provider"])
def test_delegation_uses_configured_specialist_url(monkeypatch, name):
    monkeypatch.setenv(
        f"{name.upper()}_AGENT_PUBLIC_URL", "http://localhost:23456"
    )

    async def fake_ask(agent_url, question):
        assert agent_url == "http://localhost:23456"
        assert question == "Question"
        return "Answer"

    monkeypatch.setattr(delegation, "ask_a2a_agent", fake_ask)
    assert delegation.invoke_a2a_agent(name, "Question") == "Answer"
