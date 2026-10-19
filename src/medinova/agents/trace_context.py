"""Validated trace IDs shared across backend and A2A without chat content."""

from contextvars import ContextVar
from typing import TypedDict


class TraceParent(TypedDict):
    trace_id: str
    parent_span_id: str


current_trace_parent: ContextVar[TraceParent | None] = ContextVar(
    "medinova_trace_parent", default=None
)


def parse_trace_parent(value: object) -> TraceParent | None:
    if not isinstance(value, dict) or set(value) != {"trace_id", "parent_span_id"}:
        return None
    trace_id = value["trace_id"]
    parent_id = value["parent_span_id"]
    if not isinstance(trace_id, str) or not isinstance(parent_id, str):
        return None
    if len(trace_id) != 32 or len(parent_id) != 16:
        return None
    if not all(char in "0123456789abcdef" for char in trace_id + parent_id):
        return None
    if int(trace_id, 16) == 0 or int(parent_id, 16) == 0:
        return None
    return {"trace_id": trace_id, "parent_span_id": parent_id}
