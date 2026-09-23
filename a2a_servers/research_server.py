import asyncio
import os

import uvicorn

from starlette.applications import Starlette

from a2a.server.agent_execution import (
    AgentExecutor,
    RequestContext,
)
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

from agents.research_agent import ResearchAgent


# ============================================================
# CONFIGURATION
# ============================================================

PORT = int(
    os.getenv(
        "RESEARCH_AGENT_PORT",
        "9998",
    )
)

BIND_HOST = os.getenv(
    "A2A_BIND_HOST",
    "127.0.0.1",
)

PUBLIC_URL = os.getenv(
    "RESEARCH_AGENT_PUBLIC_URL",
    f"http://127.0.0.1:{PORT}",
)


# ============================================================
# A2A EXECUTOR
# ============================================================

class ResearchAgentExecutor(AgentExecutor):

    def __init__(self) -> None:
        self.agent = ResearchAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:

        prompt = context.get_user_input()

        print(
            f"\n[A2A Research Agent] "
            f"Received question: {prompt}"
        )

        # smolagents is synchronous, while our
        # A2A server is asynchronous.
        response = await asyncio.to_thread(
            self.agent.answer_query,
            prompt,
        )

        print(
            f"\n[A2A Research Agent] "
            f"Response: {response}\n"
        )

        message = new_text_message(
            str(response)
        )

        await event_queue.enqueue_event(
            message
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        pass


# ============================================================
# AGENT SKILL
# ============================================================

research_skill = AgentSkill(
    id="health_research",

    name="Health Research",

    description=(
        "Researches healthcare information about symptoms, "
        "conditions, treatments, procedures, and healthcare "
        "options using up-to-date web resources."
    ),

    tags=[
        "healthcare",
        "research",
        "medical",
        "web-search",
    ],

    examples=[
        "What are the common treatments for sleep apnea?",
        "What are the symptoms of sleep apnea?",
        "What treatment options exist for migraines?",
        "What is cognitive behavioral therapy?",
    ],
)


# ============================================================
# AGENT CARD
# ============================================================

agent_card = AgentCard(
    name="Health Research Agent",

    description=(
        "A healthcare research agent that searches the web "
        "for current information about health conditions, "
        "symptoms, treatments, and procedures."
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
        research_skill,
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
    agent_executor=ResearchAgentExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)


# ============================================================
# A2A ROUTES
# ============================================================

routes = []

routes.extend(
    create_agent_card_routes(
        agent_card
    )
)

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
    print("Health Research A2A Agent")
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