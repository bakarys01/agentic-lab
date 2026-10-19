"""Content-free distributed observations for A2A agents and tools."""

import logging
import os
from functools import lru_cache
from typing import Any

from medinova.agents.trace_context import current_trace_parent

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client():
    from langfuse import Langfuse
    from langfuse.span_filter import is_langfuse_span

    return Langfuse(should_export_span=is_langfuse_span)


def start_observation(
    name: str, kind: str = "span", *, model: str | None = None
) -> Any | None:
    parent = current_trace_parent.get()
    if parent is None or os.getenv("LANGFUSE_ENABLED", "false").lower() != "true":
        return None
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        return None
    try:
        options = {"model": model} if model is not None else {}
        return _client().start_observation(
            name=name, as_type=kind, trace_context=parent, **options
        )
    except Exception as exc:
        logger.warning("Langfuse tracing failed (%s)", type(exc).__name__)
        return None


def finish_observation(span: Any | None, *, status: str = "ok") -> None:
    if span is None:
        return
    try:
        span.update(metadata={"status": status})
        span.end()
    except Exception as exc:
        logger.warning("Langfuse tracing failed (%s)", type(exc).__name__)


def flush() -> None:
    """Flush before a short-lived MCP stdio server exits."""
    if os.getenv("LANGFUSE_ENABLED", "false").lower() != "true":
        return
    try:
        _client().flush()
    except Exception as exc:
        logger.warning("Langfuse flush failed (%s)", type(exc).__name__)
