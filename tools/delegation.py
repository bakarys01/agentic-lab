import asyncio
from collections.abc import Callable

from smolagents import Tool

from a2a_clients.client_utils import ask_a2a_agent, get_agent_url


def invoke_a2a_agent(agent_name: str, question: str) -> str:
    return asyncio.run(
        ask_a2a_agent(
            agent_url=get_agent_url(agent_name),
            question=question,
        )
    )


class AgentTool(Tool):
    inputs = {
        "question": {
            "type": "string",
            "description": "A standalone question for the specialist.",
        }
    }
    output_type = "string"

    def __init__(
        self,
        agent_name: str,
        description: str,
        invoke: Callable[[str], str],
    ) -> None:
        self.name = f"ask_{agent_name}"
        self.description = description
        self._invoke = invoke
        super().__init__()

    def forward(self, question: str) -> str:
        return self._invoke(question)
