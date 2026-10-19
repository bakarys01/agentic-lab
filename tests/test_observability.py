"""The external telemetry boundary must never receive chat content."""

import sys
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from medinova.backend.api import create_api_app
from medinova.backend import observability
from medinova.agents.metrics import AgentMetrics, parse_agent_metrics
from medinova.agents.trace_context import current_trace_parent, parse_trace_parent
from medinova.agents import tracing


def send_chat(app, message):
    client = TestClient(app)
    client.headers["X-Requested-With"] = "fetch"
    registration = client.post(
        "/api/auth/register",
        json={"email": f"{uuid4()}@example.com", "password": "test-password-123"},
    )
    assert registration.status_code == 201
    client.headers["X-CSRF-Token"] = registration.json()["csrf_token"]
    conversation_id = client.post("/api/conversations").json()["id"]
    return client.post(
        "/api/chat",
        json={"conversation_id": conversation_id, "request_id": str(uuid4()), "message": message},
    )


class FakeSpan:
    def __init__(self):
        self.ended = False
        self.updates = []
        self.children = []

    def update(self, **kwargs):
        self.updates.append(kwargs)

    def end(self):
        self.ended = True

    def start_observation(self, **kwargs):
        child = FakeSpan()
        self.children.append((kwargs, child))
        return child


class FakeLangfuse:
    def __init__(self):
        self.events = []
        self.spans = []

    def start_observation(self, **kwargs):
        self.events.append(kwargs)
        span = FakeSpan()
        self.spans.append(span)
        return span


def test_sdk_exports_only_manually_created_spans(monkeypatch):
    predicate = object()
    monkeypatch.setitem(sys.modules, "langfuse", SimpleNamespace(Langfuse=lambda **kw: kw))
    monkeypatch.setitem(
        sys.modules, "langfuse.span_filter", SimpleNamespace(is_langfuse_span=predicate)
    )
    assert observability._client.__wrapped__()["should_export_span"] is predicate


def test_disabled_telemetry_does_not_initialize_sdk(monkeypatch):
    monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)
    monkeypatch.setattr(observability, "_client", lambda: 1 / 0)
    assert observability.start_chat_observation("request-id") is None


def test_telemetry_exports_only_whitelisted_metadata(monkeypatch, tmp_path):
    client = FakeLangfuse()
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret")
    monkeypatch.setattr(observability, "_client", lambda: client)

    class Concierge:
        def answer_query_with_metadata(self, question, history=None):
            assert len(client.spans) == 1
            assert not client.spans[0].ended
            return {"answer": "PRIVATE ANSWER", "agents_used": ["policy"], "latency_ms": 1}

    response = send_chat(
        create_api_app(Concierge(), db_path=tmp_path / "chat.db"),
        "PRIVATE MEDICAL QUESTION",
    )

    assert response.status_code == 200
    assert len(client.events) == 1
    event = client.events[0]
    assert event["name"] == "chat-request"
    assert client.spans[0].updates[0]["metadata"]["status"] == "ok"
    assert client.spans[0].updates[0]["metadata"]["agents_used"] == ["policy"]
    assert client.spans[0].updates[0]["metadata"]["latency_ms"] >= 0
    assert "PRIVATE" not in repr(event)
    assert "PRIVATE" not in repr(client.spans[0].updates)
    assert client.spans[0].ended


def test_telemetry_failure_does_not_break_chat(monkeypatch, tmp_path):
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret")
    monkeypatch.setattr(observability, "_client", lambda: 1 / 0)

    class Concierge:
        def answer_query_with_metadata(self, question, history=None):
            return {"answer": "ok", "agents_used": []}

    response = send_chat(create_api_app(Concierge(), db_path=tmp_path / "chat.db"), "hello")
    assert response.status_code == 200


def test_failed_chat_exports_status_without_error_details(monkeypatch, tmp_path):
    client = FakeLangfuse()
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret")
    monkeypatch.setattr(observability, "_client", lambda: client)

    class Concierge:
        def answer_query_with_metadata(self, question, history=None):
            raise RuntimeError("PRIVATE MEDICAL ERROR")

    response = send_chat(
        create_api_app(Concierge(), db_path=tmp_path / "chat.db"), "PRIVATE QUESTION"
    )
    assert response.status_code == 502
    assert client.spans[0].updates[0]["metadata"]["status"] == "error"
    assert "PRIVATE" not in repr(client.events)
    assert "PRIVATE" not in repr(client.spans[0].updates)


def test_model_usage_and_tool_names_are_exported_without_content(monkeypatch, tmp_path):
    client = FakeLangfuse()
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret")
    monkeypatch.setattr(observability, "_client", lambda: client)
    metrics = AgentMetrics(
        agent="policy", runtime="langchain", provider="openai", model="gpt-4o",
        duration_ms=75, steps=2, input_tokens=120, output_tokens=30,
        tools=[{"name": "search_policy", "duration_ms": 10, "status": "ok"}],
    )

    class Concierge:
        def answer_query_with_metadata(self, question, history=None):
            return {
                "answer": "PRIVATE ANSWER", "agents_used": ["policy"],
                "metrics": [metrics.model_dump(mode="json")],
            }

    response = send_chat(
        create_api_app(Concierge(), db_path=tmp_path / "chat.db"), "PRIVATE QUESTION"
    )
    assert response.status_code == 200
    root = client.spans[0]
    metadata = root.updates[0]["metadata"]
    assert metadata["tools_used"] == ["search_policy"]
    assert metadata["tool_calls"][0]["duration_ms"] == 10
    generation, child = root.children[0]
    assert generation["as_type"] == "generation"
    assert generation["name"] == "usage-policy"
    assert generation["model"] == "gpt-4o"
    assert generation["usage_details"] == {"input": 120, "output": 30}
    assert child.ended
    assert "PRIVATE" not in repr((client.events, root.updates, generation))


def test_untrusted_metric_payload_cannot_add_chat_content():
    payload = [{
        "agent": "policy", "runtime": "langchain", "provider": "openai",
        "model": "gpt-4o", "duration_ms": 2, "steps": 1,
        "question": "PRIVATE QUESTION",
    }]
    assert parse_agent_metrics(payload) == []


def test_invalid_trace_parent_is_rejected():
    assert parse_trace_parent({"trace_id": "PRIVATE QUESTION", "parent_span_id": "2" * 16}) is None
    assert parse_trace_parent({"trace_id": "1" * 32, "parent_span_id": "0" * 16}) is None


def test_distributed_observation_exports_only_trace_ids(monkeypatch):
    captured = []
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret")
    monkeypatch.setattr(
        tracing, "_client", lambda: SimpleNamespace(
            start_observation=lambda **kwargs: captured.append(kwargs) or FakeSpan()
        ),
    )
    parent = {"trace_id": "1" * 32, "parent_span_id": "2" * 16}
    token = current_trace_parent.set(parent)
    try:
        span = tracing.start_observation("agent-policy", "agent")
        tracing.finish_observation(span)
    finally:
        current_trace_parent.reset(token)

    assert captured == [{
        "name": "agent-policy", "as_type": "agent", "trace_context": parent,
    }]
    assert span.ended
