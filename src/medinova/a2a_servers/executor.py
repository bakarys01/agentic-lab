import asyncio
from google.protobuf.json_format import MessageToDict

from a2a.helpers import new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue

from medinova.agents.config_loader import load_agent_definition
from medinova.agents.runtime import AgentRuntime
from medinova.agents.trace_context import current_trace_parent, parse_trace_parent
from medinova.agents.tracing import finish_observation, start_observation


class RuntimeAgentExecutor(AgentExecutor):
    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self.agent = AgentRuntime(load_agent_definition(agent_name))

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        question = context.get_user_input()
        incoming = (
            MessageToDict(context.message.metadata).get("medinova_trace_parent")
            if getattr(context, "message", None) is not None else None
        )
        token = current_trace_parent.set(parse_trace_parent(incoming))
        span = start_observation(f"agent-{self.agent_name}", "agent")
        if span is not None:
            current_trace_parent.set({
                "trace_id": span.trace_id, "parent_span_id": span.id,
            })
        status = "error"
        try:
            answer, metrics = await asyncio.to_thread(self.agent.run_with_metrics, question)
            status = "ok"
        finally:
            finish_observation(span, status=status)
            current_trace_parent.reset(token)
        message = new_text_message(answer)
        if metrics is not None:
            message.metadata.update({"medinova_metrics": metrics.model_dump(mode="json")})
        await event_queue.enqueue_event(message)

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        pass
