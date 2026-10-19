import asyncio
from collections.abc import Callable
from time import perf_counter

from smolagents import Tool

from medinova.a2a_clients.client_utils import ask_a2a_agent, get_agent_url
from medinova.agents.metrics import AgentMetrics, ToolMetric
from medinova.agents.trace_context import current_trace_parent
from medinova.agents.tracing import finish_observation, start_observation


def invoke_a2a_agent(
    agent_name: str, question: str, include_metrics: bool = False
) -> str | tuple[str, AgentMetrics | None]:
    return asyncio.run(
        ask_a2a_agent(
            agent_url=get_agent_url(agent_name),
            question=question,
            **({"include_metrics": True} if include_metrics else {}),
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
        invoke: Callable[[str], str | tuple[str, AgentMetrics | None]],
    ) -> None:
        self.name = f"ask_{agent_name}"
        self.description = description
        self._invoke = invoke
        self.calls: list[ToolMetric] = []
        self.remote_runs: list[AgentMetrics] = []
        super().__init__()

    def forward(self, question: str) -> str:
        started = perf_counter()
        span = start_observation(f"a2a-{self.name}", "tool")
        token = current_trace_parent.set(
            {"trace_id": span.trace_id, "parent_span_id": span.id}
            if span is not None else current_trace_parent.get()
        )
        status = "error"
        try:
            result = self._invoke(question)
            if isinstance(result, tuple):
                answer, metrics = result
                if metrics is not None:
                    self.remote_runs.append(metrics)
            else:
                answer = result
            status = "ok"
            return answer
        finally:
            current_trace_parent.reset(token)
            finish_observation(span, status=status)
            self.calls.append(ToolMetric(
                name=self.name,
                duration_ms=int((perf_counter() - started) * 1000),
                status=status,
            ))
