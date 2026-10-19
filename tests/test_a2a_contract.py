import asyncio

import httpx
from google.protobuf.json_format import MessageToDict

from a2a.helpers import new_text_message

from medinova.a2a_clients import client_utils
from medinova.a2a_servers import app as a2a_app
from medinova.a2a_servers.executor import RuntimeAgentExecutor
from medinova.agents.metrics import AgentMetrics
from medinova.agents.trace_context import current_trace_parent


def test_client_and_server_exchange_a2a_message_without_model(monkeypatch):
    class FakeExecutor:
        def __init__(self, agent_name):
            assert agent_name == "policy"

        async def execute(self, context, event_queue):
            await event_queue.enqueue_event(
                new_text_message(f"Policy received: {context.get_user_input()}")
            )

        async def cancel(self, context, event_queue):
            pass

    monkeypatch.setattr(a2a_app, "RuntimeAgentExecutor", FakeExecutor)
    server = a2a_app.create_a2a_app("policy", public_url="http://testserver")
    real_async_client = httpx.AsyncClient

    def make_client(**kwargs):
        return real_async_client(
            transport=httpx.ASGITransport(app=server),
            base_url="http://testserver",
            **kwargs,
        )

    monkeypatch.setattr(client_utils.httpx, "AsyncClient", make_client)
    answer = asyncio.run(client_utils.ask_a2a_agent("http://testserver", "Deductible?"))

    assert answer == "Policy received: Deductible?"


def test_a2a_client_reads_content_free_specialist_metrics(monkeypatch):
    class FakeExecutor:
        def __init__(self, agent_name):
            pass

        async def execute(self, context, event_queue):
            message = new_text_message("PRIVATE ANSWER")
            message.metadata.update({"medinova_metrics": {
                "agent": "policy", "runtime": "langchain", "provider": "openai",
                "model": "gpt-4o", "duration_ms": 12, "steps": 1,
                "tools": [{"name": "search_policy", "duration_ms": 5, "status": "ok"}],
            }})
            await event_queue.enqueue_event(message)

        async def cancel(self, context, event_queue):
            pass

    monkeypatch.setattr(a2a_app, "RuntimeAgentExecutor", FakeExecutor)
    server = a2a_app.create_a2a_app("policy", public_url="http://testserver")
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        client_utils.httpx, "AsyncClient",
        lambda **kwargs: real_async_client(
            transport=httpx.ASGITransport(app=server),
            base_url="http://testserver", **kwargs,
        ),
    )
    answer, metrics = asyncio.run(client_utils.ask_a2a_agent(
        "http://testserver", "PRIVATE QUESTION", include_metrics=True
    ))
    assert answer == "PRIVATE ANSWER"
    assert metrics.agent == "policy"
    assert metrics.tools[0].name == "search_policy"
    assert "PRIVATE" not in repr(metrics)


def test_a2a_request_propagates_only_trace_ids(monkeypatch):
    parent = {"trace_id": "1" * 32, "parent_span_id": "2" * 16}

    class FakeExecutor:
        def __init__(self, agent_name):
            pass

        async def execute(self, context, event_queue):
            metadata = MessageToDict(context.message.metadata)
            assert metadata == {"medinova_trace_parent": parent}
            await event_queue.enqueue_event(new_text_message("PRIVATE ANSWER"))

        async def cancel(self, context, event_queue):
            pass

    monkeypatch.setattr(a2a_app, "RuntimeAgentExecutor", FakeExecutor)
    server = a2a_app.create_a2a_app("policy", public_url="http://testserver")
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        client_utils.httpx, "AsyncClient",
        lambda **kwargs: real_async_client(
            transport=httpx.ASGITransport(app=server),
            base_url="http://testserver", **kwargs,
        ),
    )
    token = current_trace_parent.set(parent)
    try:
        answer = asyncio.run(client_utils.ask_a2a_agent(
            "http://testserver", "PRIVATE QUESTION"
        ))
    finally:
        current_trace_parent.reset(token)
    assert answer == "PRIVATE ANSWER"


def test_specialist_executor_attaches_validated_metrics_only():
    metrics = AgentMetrics(
        agent="policy", runtime="langchain", provider="openai",
        model="gpt-4o", duration_ms=9, steps=1,
    )

    class FakeRuntime:
        def run_with_metrics(self, question):
            return "PRIVATE ANSWER", metrics

    class Queue:
        async def enqueue_event(self, message):
            self.message = message

    executor = RuntimeAgentExecutor("policy")
    executor.agent = FakeRuntime()
    queue = Queue()
    asyncio.run(executor.execute(
        type("Context", (), {"get_user_input": lambda self: "PRIVATE QUESTION"})(),
        queue,
    ))
    assert queue.message.metadata["medinova_metrics"]["agent"] == "policy"
    assert "PRIVATE" not in str(queue.message.metadata)


def test_specialist_observation_is_child_of_incoming_trace(monkeypatch):
    from medinova.a2a_servers import executor as executor_module

    parent = {"trace_id": "1" * 32, "parent_span_id": "2" * 16}
    seen = []

    class Span:
        trace_id = "1" * 32
        id = "3" * 16

    def start(name, kind):
        seen.append((name, kind, current_trace_parent.get()))
        return Span()

    class FakeRuntime:
        def run_with_metrics(self, question):
            seen.append(("runtime", current_trace_parent.get()))
            return "PRIVATE ANSWER", None

    class Queue:
        async def enqueue_event(self, message):
            self.message = message

    monkeypatch.setattr(executor_module, "start_observation", start)
    monkeypatch.setattr(executor_module, "finish_observation", lambda *a, **kw: None)
    executor = RuntimeAgentExecutor("policy")
    executor.agent = FakeRuntime()
    message = new_text_message("PRIVATE QUESTION")
    message.metadata.update({"medinova_trace_parent": parent})
    context = type("Context", (), {
        "message": message,
        "get_user_input": lambda self: "PRIVATE QUESTION",
    })()
    asyncio.run(executor.execute(context, Queue()))

    assert seen[0] == ("agent-policy", "agent", parent)
    assert seen[1] == ("runtime", {"trace_id": "1" * 32,
                                   "parent_span_id": "3" * 16})
    assert current_trace_parent.get() is None
