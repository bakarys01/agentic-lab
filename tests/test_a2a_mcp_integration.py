"""Exercise the A2A-to-MCP boundary without model or external services."""

import asyncio
import json

import httpx
import pytest
from a2a.helpers import new_text_message

from medinova.a2a_clients import client_utils
from medinova.a2a_servers import app as a2a_app
from medinova.tools.mcp_connector import load_mcp_tools


@pytest.mark.parametrize(
    "agent_name,server_name,question,tool_arguments",
    [
        ("policy", "policy_documents", "deductible", {"query": "deductible"}),
        (
            "healthcare_provider",
            "healthcare_providers",
            "Psychiatrists in Paris",
            {"city": "Paris", "specialty": "Psychiatry"},
        ),
    ],
)
def test_a2a_request_calls_real_mcp_tool(
    monkeypatch, agent_name, server_name, question, tool_arguments
):
    class ToolExecutor:
        def __init__(self, configured_name):
            assert configured_name == agent_name

        async def execute(self, context, event_queue):
            assert context.get_user_input() == question
            tools = await load_mcp_tools(server_name)
            assert len(tools) == 1
            result = await tools[0].ainvoke(tool_arguments)
            assert isinstance(result, list) and len(result) == 1
            assert result[0]["type"] == "text"
            await event_queue.enqueue_event(new_text_message(result[0]["text"]))

        async def cancel(self, context, event_queue):
            pass

    monkeypatch.setattr(a2a_app, "RuntimeAgentExecutor", ToolExecutor)
    server = a2a_app.create_a2a_app(agent_name, public_url="http://testserver")
    real_async_client = httpx.AsyncClient

    def in_memory_client(**kwargs):
        return real_async_client(
            transport=httpx.ASGITransport(app=server),
            base_url="http://testserver",
            **kwargs,
        )

    monkeypatch.setattr(client_utils.httpx, "AsyncClient", in_memory_client)
    answer = asyncio.run(client_utils.ask_a2a_agent("http://testserver", question))

    if agent_name == "policy":
        assert "SOURCE: Insurance Policy" in answer
        assert "PAGE:" in answer
        assert "deductible" in answer.casefold()
    else:
        doctors = json.loads(answer)
        assert doctors
        assert all(doctor["address"]["city"] == "Paris" for doctor in doctors)
        assert all(doctor["specialty"] == "Psychiatry" for doctor in doctors)
