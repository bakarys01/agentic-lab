import os

import httpx
from google.protobuf.json_format import MessageToDict

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_message_text, new_text_message
from a2a.types import (
    Role,
    SendMessageConfiguration,
    SendMessageRequest,
)
from medinova.agents.config_loader import load_a2a_config
from medinova.agents.metrics import AgentMetrics
from medinova.agents.trace_context import current_trace_parent


def _text_and_metrics(message, include_metrics: bool):
    answer = get_message_text(message)
    if not include_metrics:
        return answer
    payload = MessageToDict(message.metadata).get("medinova_metrics")
    try:
        metrics = AgentMetrics.model_validate(payload) if payload else None
    except ValueError:
        metrics = None
    return answer, metrics

def get_agent_url(name: str) -> str:
    port = load_a2a_config(name)["port"]
    public_url = os.getenv(
        f"{name.upper()}_AGENT_PUBLIC_URL",
        f"http://127.0.0.1:{port}",
    )
    return public_url.rstrip("/")

async def ask_a2a_agent(
    agent_url: str,
    question: str,
    timeout: float = 120.0,
    include_metrics: bool = False,
) -> str | tuple[str, AgentMetrics | None]:
    """
    Send a question to an A2A agent and return its text response.

    This function contains the generic A2A communication logic.
    """

    httpx_client = httpx.AsyncClient(
        timeout=httpx.Timeout(timeout)
    )

    client_config = ClientConfig(
        httpx_client=httpx_client
    )

    client = await create_client(
        agent_url,
        client_config=client_config,
    )

    message = new_text_message(
        question,
        role=Role.ROLE_USER,
    )
    trace_parent = current_trace_parent.get()
    if trace_parent is not None:
        message.metadata.update({"medinova_trace_parent": trace_parent})

    request = SendMessageRequest(
        message=message,
        configuration=SendMessageConfiguration(
            return_immediately=False,
        ),
    )

    try:
        async for response in client.send_message(request):

            if response.HasField("message"):
                return _text_and_metrics(response.message, include_metrics)

            if response.HasField("task"):
                task = response.task

                # Some agents may return the answer through
                # the task status message.
                if (
                    task.HasField("status")
                    and task.status.HasField("message")
                ):
                    return _text_and_metrics(task.status.message, include_metrics)

        answer = "The agent did not return a text response."
        return (answer, None) if include_metrics else answer

    finally:
        await client.close()
        await httpx_client.aclose()
