import asyncio

import pytest

from agents.models import create_model
from tools.mcp_connector import load_mcp_tools


@pytest.mark.parametrize(
    "server,expected",
    [
        ("policy_documents", "search_policy"),
        ("research_web", "web_search"),
        ("healthcare_providers", "list_doctors"),
        ("medication_catalog", "get_medication"),
    ],
)
def test_configured_mcp_server_exposes_selected_tool(server, expected, monkeypatch):
    if server == "medication_catalog":
        for name in ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD"):
            monkeypatch.setenv(name, "test-value")
    async def check():
        tools = await load_mcp_tools(server)
        assert [tool.name for tool in tools] == [expected]
        if server == "policy_documents":
            result = await tools[0].ainvoke({"query": "deductible"})
            content = str(result)
            assert "PAGE:" in content
            assert "deductible" in content.casefold()

    asyncio.run(check())


def test_research_tool_preserves_source_urls(monkeypatch):
    from mcp_servers import research

    class FakeSearch:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def text(self, query, max_results):
            assert query == "sleep apnea"
            assert max_results == 10
            return [{"title": "Medical source", "href": "https://example.org/medical", "body": "A source excerpt"}]

    monkeypatch.setattr(research, "DDGS", FakeSearch)
    result = research.web_search("sleep apnea")
    assert "https://example.org/medical" in result
    assert "A source excerpt" in result


def test_langchain_openai_model_uses_configured_profile(monkeypatch):
    import langchain_openai

    captured = {}
    def fake_model(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(langchain_openai, "ChatOpenAI", fake_model)
    create_model("default", "langchain")
    assert captured["model"] == "gpt-4o"
    assert captured["api_key"] == "test-key"
