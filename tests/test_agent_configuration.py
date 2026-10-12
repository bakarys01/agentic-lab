import pytest

from a2a_clients import client_utils
from agents.config_loader import load_agent_definition, load_mcp_config
from tools import delegation


@pytest.mark.parametrize(
    "name,server,tool",
    [
        ("policy", "policy_documents", "search_policy"),
        ("research", "research_web", "web_search"),
        ("healthcare_provider", "healthcare_providers", "list_doctors"),
        ("medication", "medication_catalog", "get_medication"),
    ],
)
def test_specialist_tools_are_selected_from_mcp(name, server, tool):
    definition = load_agent_definition(name)
    assert definition.runtime == "langchain"
    assert definition.tools == (tool,)
    assert definition.mcp_servers == (server,)
    assert tool in load_mcp_config(server)["allowed_tools"]


def test_medication_mcp_declares_only_database_environment():
    assert load_mcp_config("medication_catalog")["env_vars"] == (
        "PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD"
    )


def test_concierge_keeps_empty_tool_selector_and_a2a_delegates():
    definition = load_agent_definition("concierge")
    assert definition.tools == ()
    assert definition.mcp_servers == ()
    assert definition.delegates == ("policy", "research", "healthcare_provider", "medication")


@pytest.mark.parametrize(
    "name,port",
    [
        ("policy", 9999),
        ("research", 9998),
        ("healthcare_provider", 9997),
        ("medication", 9996),
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

@pytest.mark.parametrize("name", ["policy", "research", "healthcare_provider", "medication"])
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
