"""Time smolagents model calls without retaining input or output content."""

from typing import Any

from medinova.agents.tracing import finish_observation, start_observation


class TracedModel:
    def __init__(self, model: Any, agent_name: str) -> None:
        self._model = model
        self._agent_name = agent_name

    def __getattr__(self, name: str) -> Any:
        return getattr(self._model, name)

    def generate(self, *args: Any, **kwargs: Any) -> Any:
        span = start_observation(
            f"model-{self._agent_name}", "generation",
            model=self._model.model_id,
        )
        status = "error"
        try:
            result = self._model.generate(*args, **kwargs)
            status = "ok"
            return result
        finally:
            finish_observation(span, status=status)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.generate(*args, **kwargs)
