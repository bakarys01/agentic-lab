"""Reusable content-free instrumentation for local FastMCP servers."""

import os

from mcp.server.fastmcp import FastMCP

from medinova.agents.trace_context import current_trace_parent, parse_trace_parent
from medinova.agents.tracing import finish_observation, flush, start_observation


class TracedFastMCP(FastMCP):
    async def call_tool(self, name: str, arguments: dict):
        parent = parse_trace_parent({
            "trace_id": os.getenv("MEDINOVA_TRACE_ID"),
            "parent_span_id": os.getenv("MEDINOVA_PARENT_SPAN_ID"),
        })
        token = current_trace_parent.set(parent)
        span = start_observation(f"mcp-{name}", "tool")
        status = "error"
        try:
            result = await super().call_tool(name, arguments)
            status = "ok"
            return result
        finally:
            finish_observation(span, status=status)
            current_trace_parent.reset(token)
            if span is not None:
                flush()
