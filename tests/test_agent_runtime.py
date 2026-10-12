from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from medinova.agents.config_loader import load_agent_definition
from medinova.agents.runtime import AgentRuntime


def test_run_returns_text_and_includes_recent_history(monkeypatch):
    import medinova.agents.runtime as runtime_module

    fake_agent = Mock()
    fake_agent.run.return_value = "Policy answer"
    monkeypatch.setattr(runtime_module, "create_model", lambda **_: object())
    monkeypatch.setattr(runtime_module, "ToolCallingAgent", lambda **_: fake_agent)

    runtime = AgentRuntime(load_agent_definition("concierge"))
    history = [
        {"role": "user", "content": "Tell me about therapy"},
        {"role": "assistant", "content": "Which benefit?"},
    ]

    assert runtime.run("What is the cost?", history=history) == "Policy answer"
    task = fake_agent.run.call_args.args[0]
    assert "Tell me about therapy" in task
    assert "User question:\nWhat is the cost?" in task


def test_langchain_agent_receives_only_tools_selected_by_definition(monkeypatch):
    import medinova.agents.runtime as runtime_module

    discovered = []
    async def fake_load(server):
        discovered.append(server)
        return [SimpleNamespace(name="search_policy"), SimpleNamespace(name="unused_tool")]

    class FakeAgent:
        async def ainvoke(self, payload):
            return {"messages": [SimpleNamespace(content="Policy answer")]}

    captured = {}
    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return FakeAgent()

    monkeypatch.setattr(runtime_module, "load_mcp_tools", fake_load)
    monkeypatch.setattr(runtime_module, "create_model", lambda **_: object())
    monkeypatch.setattr(runtime_module, "create_agent", fake_create_agent)
    runtime = AgentRuntime(load_agent_definition("policy"))

    assert runtime.run("What is the deductible?") == "Policy answer"
    assert discovered == ["policy_documents"]
    assert [tool.name for tool in captured["tools"]] == ["search_policy"]


def test_missing_selected_mcp_tool_fails_before_model_call(monkeypatch):
    import medinova.agents.runtime as runtime_module

    async def fake_load(server):
        return [SimpleNamespace(name="different_tool")]

    monkeypatch.setattr(runtime_module, "load_mcp_tools", fake_load)
    monkeypatch.setattr(runtime_module, "create_model", lambda **_: pytest.fail("Model should not be created"))
    runtime = AgentRuntime(load_agent_definition("policy"))
    with pytest.raises(ValueError, match="search_policy"):
        runtime.run("Question")


def test_duplicate_selected_tool_across_mcp_servers_is_rejected(monkeypatch):
    from dataclasses import replace
    import medinova.agents.runtime as runtime_module

    async def fake_load(server):
        return [SimpleNamespace(name="search_policy")]

    monkeypatch.setattr(runtime_module, "load_mcp_tools", fake_load)
    definition = replace(
        load_agent_definition("policy"),
        mcp_servers=("policy_documents", "another_server"),
    )
    with pytest.raises(ValueError, match="Duplicate tool names"):
        AgentRuntime(definition).run("Question")


def test_run_does_not_reuse_previous_history(monkeypatch):
    import medinova.agents.runtime as runtime_module

    fake_agent = Mock()
    fake_agent.run.return_value = "Answer"
    monkeypatch.setattr(runtime_module, "create_model", lambda **_: object())
    monkeypatch.setattr(runtime_module, "ToolCallingAgent", lambda **_: fake_agent)

    runtime = AgentRuntime(load_agent_definition("concierge"))
    history = [
        {"role": "user", "content": "sleep apnea"},
        {"role": "assistant", "content": "CPAP"},
    ]
    runtime.run("Is it covered?", history=history)
    runtime.run("New topic")

    first_task = fake_agent.run.call_args_list[0].args[0]
    second_task = fake_agent.run.call_args_list[1].args[0]
    assert "sleep apnea" in first_task
    assert "sleep apnea" not in second_task


def test_metadata_reports_only_called_delegates(monkeypatch):
    import medinova.agents.runtime as runtime_module

    fake_agent = Mock()
    fake_agent.run.return_value = "Combined answer"
    fake_agent.memory.steps = [
        SimpleNamespace(tool_calls=[SimpleNamespace(name="ask_policy")])
    ]
    monkeypatch.setattr(runtime_module, "create_model", lambda **_: object())
    monkeypatch.setattr(runtime_module, "ToolCallingAgent", lambda **_: fake_agent)

    runtime = AgentRuntime(load_agent_definition("concierge"))
    payload = runtime.answer_query_with_metadata("Is therapy covered?")

    assert payload["answer"] == "Combined answer"
    assert payload["agents_used"] == ["policy"]
    assert isinstance(payload["latency_ms"], int)
    assert payload["latency_ms"] >= 0


@pytest.mark.parametrize("available", [True, False])
def test_health_checks_all_a2a_delegate_cards(monkeypatch, available):
    import medinova.agents.runtime as runtime_module

    visited = []
    monkeypatch.setattr(
        runtime_module,
        "get_agent_url",
        lambda name: f"http://{name}.example:1234",
        raising=False,
    )

    def get(url, timeout):
        visited.append(url)
        if not available:
            raise httpx.ConnectError("offline")
        return SimpleNamespace(status_code=200)

    monkeypatch.setattr(runtime_module.httpx, "get", get, raising=False)
    health = AgentRuntime(load_agent_definition("concierge")).get_health()

    assert visited == [
        f"http://{name}.example:1234/.well-known/agent-card.json"
        for name in ("policy", "research", "healthcare_provider", "medication")
    ]
    expected = "available" if available else "unavailable"
    assert all(
        health["services"][name]["status"] == expected
        for name in ("policy", "research", "healthcare_provider", "medication")
    )
    assert health["status"] == ("ok" if available else "degraded")


def test_langchain_runtime_reuses_event_loop_across_questions(monkeypatch):
    import asyncio

    runtime = AgentRuntime(load_agent_definition("medication"))
    loop_ids = []

    async def fake_run(question):
        loop_ids.append(id(asyncio.get_running_loop()))
        return question

    monkeypatch.setattr(runtime, "_run_langchain", fake_run)

    assert runtime.run("first") == "first"
    assert runtime.run("second") == "second"
    assert loop_ids[0] == loop_ids[1]
