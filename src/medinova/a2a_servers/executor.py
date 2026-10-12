import asyncio

from a2a.helpers import new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue

from medinova.agents.config_loader import load_agent_definition
from medinova.agents.runtime import AgentRuntime


class RuntimeAgentExecutor(AgentExecutor):
    def __init__(self, agent_name: str) -> None:
        self.agent = AgentRuntime(load_agent_definition(agent_name))

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        question = context.get_user_input()
        answer = await asyncio.to_thread(self.agent.run, question)
        await event_queue.enqueue_event(new_text_message(answer))

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        pass