import asyncio

import httpx

from a2a.helpers import new_text_message

from medinova.a2a_clients import client_utils
from medinova.a2a_servers import app as a2a_app


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
