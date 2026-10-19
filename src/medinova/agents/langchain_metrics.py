"""Capture tool timing without retaining LangChain tool arguments or results."""

from time import perf_counter
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler

from medinova.agents.metrics import ToolMetric
from medinova.agents.tracing import finish_observation, start_observation


class ToolCallRecorder(AsyncCallbackHandler):
    def __init__(self, agent_name: str | None = None, model: str | None = None) -> None:
        self._started: dict[UUID, tuple[str, float]] = {}
        self.calls: list[ToolMetric] = []
        self._spans: dict[UUID, object] = {}
        self._model_spans: dict[UUID, object] = {}
        self._agent_name = agent_name
        self._model = model

    async def on_chat_model_start(
        self, serialized: dict, messages: list, *, run_id: UUID, **kwargs
    ) -> None:
        self._start_model(run_id)

    async def on_llm_start(
        self, serialized: dict, prompts: list[str], *, run_id: UUID, **kwargs
    ) -> None:
        self._start_model(run_id)

    async def on_llm_end(self, response, *, run_id: UUID, **kwargs) -> None:
        finish_observation(self._model_spans.pop(run_id, None))

    async def on_llm_error(
        self, error: BaseException, *, run_id: UUID, **kwargs
    ) -> None:
        finish_observation(self._model_spans.pop(run_id, None), status="error")

    def _start_model(self, run_id: UUID) -> None:
        if self._agent_name and self._model and run_id not in self._model_spans:
            self._model_spans[run_id] = start_observation(
                f"model-{self._agent_name}", "generation", model=self._model
            )

    async def on_tool_start(
        self, serialized: dict, input_str: str, *, run_id: UUID, **kwargs
    ) -> None:
        name = (serialized or {}).get("name") or kwargs.get("name")
        if isinstance(name, str):
            self._started[run_id] = (name, perf_counter())
            self._spans[run_id] = start_observation(f"tool-{name}", "tool")

    async def on_tool_end(self, output, *, run_id: UUID, **kwargs) -> None:
        self._finish(run_id, "ok")

    async def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs) -> None:
        self._finish(run_id, "error")

    def _finish(self, run_id: UUID, status: str) -> None:
        finish_observation(self._spans.pop(run_id, None), status=status)
        started = self._started.pop(run_id, None)
        if started is None:
            return
        name, timestamp = started
        try:
            metric = ToolMetric(
                name=name,
                duration_ms=int((perf_counter() - timestamp) * 1000),
                status=status,
            )
        except ValueError:
            return
        self.calls.append(metric)
