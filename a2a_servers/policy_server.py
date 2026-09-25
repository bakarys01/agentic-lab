import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import uvicorn

from starlette.applications import Starlette

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)

from a2a.helpers import new_text_message

from agents.policy_agent import PolicyAgent


# ============================================================
# CONFIGURATION
# ============================================================

PORT = int(
    os.getenv(
        "POLICY_AGENT_PORT",
        "9999",
    )
)

BIND_HOST = os.getenv(
    "A2A_BIND_HOST",
    "127.0.0.1",
)

PUBLIC_URL = os.getenv(
    "POLICY_AGENT_PUBLIC_URL",
    os.getenv("A2A_PUBLIC_URL", f"http://127.0.0.1:{PORT}"),
)


# ============================================================
# A2A EXECUTOR
# ============================================================

class PolicyAgentExecutor(AgentExecutor):
    """
    Adapter between the A2A protocol and our smolagents
    PolicyAgent.
    """

    def __init__(self) -> None:
        self.agent = PolicyAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:

        # Get the text sent by the A2A client
        prompt = context.get_user_input()

        print(f"\n[A2A] Received question: {prompt}")

        # PolicyAgent / smolagents is synchronous.
        # Run it in a worker thread so we don't block
        # the async A2A server.
        response = await asyncio.to_thread(
            self.agent.answer_query,
            prompt,
        )

        print(f"[A2A] Response: {response}\n")

        # A2A v1 message
        message = new_text_message(
            str(response)
        )

        await event_queue.enqueue_event(message)

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        pass


# ============================================================
# AGENT CARD
# ============================================================

policy_skill = AgentSkill(
    id="insurance_coverage",

    name="Insurance Policy Coverage",

    description=(
        "Answers questions about health insurance coverage, "
        "copays, deductibles, coinsurance, benefits, "
        "and exclusions."
    ),

    tags=[
        "insurance",
        "healthcare",
        "coverage",
        "policy",
    ],

    examples=[
        "What does my insurance policy cover?",
        "Are mental health services covered?",
        "How much would I pay for therapy?",
        "What is my deductible?",
        "What is the copay for a specialist?",
    ],
)


agent_card = AgentCard(
    name="Insurance Policy Agent",

    description=(
        "A health insurance policy assistant that retrieves "
        "information from an insurance policy."
    ),

    version="1.0.0",

    capabilities=AgentCapabilities(
        streaming=False,
    ),

    default_input_modes=[
        "text/plain",
    ],

    default_output_modes=[
        "text/plain",
    ],

    skills=[
        policy_skill,
    ],

    supported_interfaces=[
        AgentInterface(
            url=PUBLIC_URL,
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        )
    ],
)


# ============================================================
# REQUEST HANDLER
# ============================================================

request_handler = DefaultRequestHandler(
    agent_executor=PolicyAgentExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)


# ============================================================
# A2A ROUTES
# ============================================================

routes = []

# Agent discovery
routes.extend(
    create_agent_card_routes(
        agent_card
    )
)

# A2A JSON-RPC endpoint
routes.extend(
    create_jsonrpc_routes(
        request_handler,
        rpc_url="/",
    )
)


# ============================================================
# STARLETTE APPLICATION
# ============================================================

app = Starlette(
    routes=routes
)


# ============================================================
# ENTRY POINT
# ============================================================

def main() -> None:

    print("=" * 60)
    print("Insurance Policy A2A Agent")
    print("=" * 60)

    print(f"Bind:       {BIND_HOST}:{PORT}")
    print(f"Public URL: {PUBLIC_URL}")
    print("Protocol:   A2A 1.0 / JSON-RPC")
    print("=" * 60)

    uvicorn.run(
        app,
        host=BIND_HOST,
        port=PORT,
    )


if __name__ == "__main__":
    main()
