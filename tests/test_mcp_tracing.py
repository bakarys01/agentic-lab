"""Local MCP subprocesses receive only trace IDs and record tool duration."""

import asyncio

from mcp.server.fastmcp import FastMCP

from medinova.agents.trace_context import current_trace_parent
from medinova.mcp_servers import traced_server
from medinova.tools import mcp_connector


def test_mcp_connection_carries_valid_trace_parent(monkeypatch):
    parent = {"trace_id": "1" * 32, "parent_span_id": "2" * 16}
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret")
    token = current_trace_parent.set(parent)
    try:
        environment = mcp_connector._stdio_environment(())
    finally:
        current_trace_parent.reset(token)

    assert environment["MEDINOVA_TRACE_ID"] == parent["trace_id"]
    assert environment["MEDINOVA_PARENT_SPAN_ID"] == parent["parent_span_id"]
    assert environment["LANGFUSE_PUBLIC_KEY"] == "test-public"
    assert environment["LANGFUSE_SECRET_KEY"] == "test-secret"
    assert "PRIVATE PROMPT" not in repr(environment)


def test_mcp_server_span_wraps_real_tool_execution(monkeypatch):
    parent = {"trace_id": "1" * 32, "parent_span_id": "2" * 16}
    monkeypatch.setenv("MEDINOVA_TRACE_ID", parent["trace_id"])
    monkeypatch.setenv("MEDINOVA_PARENT_SPAN_ID", parent["parent_span_id"])
    events = []

    async def fake_call(self, name, arguments):
        events.append(("call", name, current_trace_parent.get()))
        return "PRIVATE RESULT"

    monkeypatch.setattr(FastMCP, "call_tool", fake_call)
    monkeypatch.setattr(
        traced_server, "start_observation",
        lambda name, kind: events.append(("start", name, kind,
                                         current_trace_parent.get())) or object(),
    )
    monkeypatch.setattr(
        traced_server, "finish_observation",
        lambda span, *, status="ok": events.append(("finish", status)),
    )
    monkeypatch.setattr(traced_server, "flush", lambda: None)

    server = traced_server.TracedFastMCP("test")
    result = asyncio.run(server.call_tool("search_policy", {"query": "PRIVATE"}))

    assert result == "PRIVATE RESULT"
    assert events == [
        ("start", "mcp-search_policy", "tool", parent),
        ("call", "search_policy", parent),
        ("finish", "ok"),
    ]
    assert current_trace_parent.get() is None
    assert "PRIVATE" not in repr(events)
