# agents/concierge_agent.py

import time
from typing import Any

import httpx
from a2a_clients.client_utils import get_agent_url
from smolagents import (
    OpenAIServerModel,
    ToolCallingAgent,
)

from tools.concierge_tools import (
    ask_policy,
    ask_research,
    clear_agent_usage,
)


class ConciergeAgent:
    """
    Main healthcare concierge.

    Routes questions to specialized agents through A2A
    and synthesizes their responses.
    """

    def __init__(self) -> None:

        model = OpenAIServerModel(
            model_id="gpt-4o"
        )

        self.agent = ToolCallingAgent(
            model=model,
            tools=[
                ask_policy,
                ask_research,
            ],
            max_steps=8,
            verbosity_level=0,
        )

    def _build_task(self, query: str) -> str:
        return f"""
You are a healthcare concierge agent.

You have access to two specialized agents.

1. ask_policy
   Use this agent for questions about the user's insurance policy:
   - coverage
   - copays
   - coinsurance
   - deductibles
   - benefits
   - exclusions
   - in-network vs out-of-network costs

2. ask_research
   Use this agent for general healthcare research:
   - medical conditions
   - symptoms
   - treatments
   - procedures
   - healthcare options

Your job is to determine which specialized agent is needed.

Rules:

- For insurance-specific questions, use ask_policy.
- For general medical or healthcare research, use ask_research.
- If the question contains both insurance and medical research
  aspects, call BOTH agents.
- Do not answer specialized questions from your own knowledge
  when one of the specialized agents should be used.
- Preserve important details from the specialist responses.
- Clearly distinguish insurance policy information from general
  healthcare information.
- Do not invent information that was not provided by the
  specialized agents.
- After collecting the required information, synthesize it into
  one clear response for the user.

User question:

{query}
"""

    def answer_query(
        self,
        query: str,
    ) -> str:
        clear_agent_usage()
        response = self.agent.run(self._build_task(query))
        return str(response)

    def answer_query_with_metadata(
        self,
        query: str,
    ) -> dict[str, Any]:
        clear_agent_usage()
        started = time.perf_counter()
        response = self.agent.run(self._build_task(query))
        latency_ms = int((time.perf_counter() - started) * 1000)
        # Parallel tools run in copied contexts. Completed memory is authoritative
        # because ContextVar updates inside those threads do not reach this thread.
        tool_names = {
            call.name
            for step in self.agent.memory.steps
            for call in (getattr(step, "tool_calls", None) or [])
        }

        return {
            "answer": str(response),
            "agents_used": [name for name in ("policy", "research") if f"ask_{name}" in tool_names],
            "latency_ms": latency_ms,
        }

    def get_health(self) -> dict[str, Any]:
        services = {
            "concierge": {"status": "available"},
            "policy": {"status": "unknown"},
            "research": {"status": "unknown"},
        }

        for name in ("policy", "research"):
            url = f"{get_agent_url(name).rstrip('/')}/.well-known/agent-card.json"
            try:
                response = httpx.get(url, timeout=3.0)
                services[name]["status"] = "available" if response.status_code == 200 else "unavailable"
            except httpx.HTTPError:
                services[name]["status"] = "unavailable"

        return {
            "status": "ok" if all(service["status"] == "available" for service in services.values()) else "degraded",
            "services": services,
        }
