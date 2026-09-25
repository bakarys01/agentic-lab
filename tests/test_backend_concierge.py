from types import SimpleNamespace

from agents.concierge_agent import ConciergeAgent
import httpx
import pytest


def test_metadata_includes_tools_executed_in_parallel():
    concierge = ConciergeAgent.__new__(ConciergeAgent)
    concierge.agent = SimpleNamespace(
        run=lambda task: "Combined response",
        memory=SimpleNamespace(steps=[
            SimpleNamespace(),
            SimpleNamespace(tool_calls=[
                SimpleNamespace(name="ask_research"),
                SimpleNamespace(name="ask_policy"),
                SimpleNamespace(name="final_answer"),
            ]),
        ]),
    )
    result = concierge.answer_query_with_metadata("Treatments and coverage?")
    assert result["answer"] == "Combined response"
    assert result["agents_used"] == ["policy", "research"]


@pytest.mark.parametrize("available", [True, False])
def test_health_uses_configured_specialist_urls(monkeypatch, available):
    import agents.concierge_agent as module
    monkeypatch.setattr(module, "get_agent_url", lambda name: f"http://{name}.example:1234/")
    visited = []

    def get(url, timeout):
        visited.append(url)
        if not available:
            raise httpx.ConnectError("offline")
        return SimpleNamespace(status_code=200)

    monkeypatch.setattr(module.httpx, "get", get)
    health = ConciergeAgent.__new__(ConciergeAgent).get_health()
    assert visited == [
        "http://policy.example:1234/.well-known/agent-card.json",
        "http://research.example:1234/.well-known/agent-card.json",
    ]
    assert health["status"] == ("ok" if available else "degraded")
