"""Content-free execution metrics shared across agent and A2A boundaries."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ToolMetric(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    duration_ms: int = Field(ge=0)
    status: Literal["ok", "error"]


class AgentMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    agent: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    runtime: Literal["smolagents", "langchain"]
    provider: Literal["openai", "huggingface"]
    model: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9_./:@+-]+$")
    duration_ms: int = Field(ge=0)
    steps: int = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    tools: tuple[ToolMetric, ...] = ()


def parse_agent_metrics(payload: object) -> list[AgentMetrics]:
    """Accept only validated metric records at the backend boundary."""
    if not isinstance(payload, list):
        return []
    parsed = []
    for item in payload:
        try:
            parsed.append(AgentMetrics.model_validate(item))
        except (ValidationError, TypeError, ValueError):
            continue
    return parsed
