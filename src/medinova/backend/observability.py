"""Opt-in, metadata-only chat telemetry.

Do not use framework callbacks here: they can export prompts, tool arguments and
model responses. The payload below is an explicit allowlist.
"""

import logging
import os
from functools import lru_cache
from typing import Any

from medinova.agents.metrics import AgentMetrics
from medinova.agents.trace_context import TraceParent

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client():
    from langfuse import Langfuse
    from langfuse.span_filter import is_langfuse_span

    # The default SDK filter also exports selected GenAI framework spans.
    # Restrict export to our manually created event to prevent content capture.
    return Langfuse(should_export_span=is_langfuse_span)


def start_chat_observation(request_id: str) -> Any | None:
    """Start a content-free span before the agent work begins."""
    if os.getenv("LANGFUSE_ENABLED", "false").lower() != "true":
        return None
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        logger.warning("Langfuse telemetry disabled: credentials are missing")
        return None

    try:
        return _client().start_observation(
            name="chat-request", as_type="span", metadata={"request_id": request_id}
        )
    except Exception as exc:
        logger.warning("Langfuse telemetry failed (%s)", type(exc).__name__)
        return None


def observation_parent(span: Any | None) -> TraceParent | None:
    if span is None:
        return None
    trace_id = getattr(span, "trace_id", None)
    span_id = getattr(span, "id", None)
    if isinstance(trace_id, str) and isinstance(span_id, str):
        return {"trace_id": trace_id, "parent_span_id": span_id}
    return None


def finish_chat_observation(
    span: Any | None,
    status: str,
    latency_ms: int,
    agents_used: list[str],
    runs: list[AgentMetrics] | None = None,
) -> None:
    """End the span with only allowlisted metadata, even after agent failure."""
    if span is None:
        return

    runs = runs or []
    tool_calls = [
        {"agent": run.agent, **call.model_dump()}
        for run in runs for call in run.tools
    ]
    metadata = {
        "status": status,
        "latency_ms": latency_ms,
        "agents_used": list(agents_used),
        "tools_used": sorted({call["name"] for call in tool_calls}),
        "tool_calls": tool_calls,
        "agent_runs": [
            {
                "agent": run.agent,
                "runtime": run.runtime,
                "provider": run.provider,
                "model": run.model,
                "duration_ms": run.duration_ms,
                "steps": run.steps,
                "input_tokens": run.input_tokens,
                "output_tokens": run.output_tokens,
            }
            for run in runs
        ],
    }
    try:
        try:
            span.update(metadata=metadata)
            for run in runs:
                usage = {
                    key: count for key, count in (
                        ("input", run.input_tokens),
                        ("output", run.output_tokens),
                    ) if count is not None
                }
                if usage:
                    generation = span.start_observation(
                        name=f"usage-{run.agent}",
                        as_type="generation",
                        model=run.model,
                        usage_details=usage,
                        metadata={"agent": run.agent, "provider": run.provider},
                    )
                    generation.end()
        finally:
            span.end()
    except Exception as exc:
        # Observability must not affect the chat response or log SDK payloads.
        logger.warning("Langfuse telemetry failed (%s)", type(exc).__name__)
