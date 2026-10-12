"""Bounded conversational context; persistence belongs to the backend."""

import json
from typing import Any


def recent_history(
    history: list[dict[str, Any]] | None,
    max_pairs: int = 6,
    max_chars: int = 16000,
) -> list[dict[str, str]]:
    """Keep a recent suffix of complete user/assistant pairs without mutation.

    The character budget covers serialized JSON. An oversized pair is never
    split: context stops there, preserving the most recent coherent suffix.
    """
    pairs = []
    pending = None
    for message in history or []:
        role, content = message.get("role"), message.get("content")
        if message.get("status", "complete") != "complete" or not isinstance(content, str):
            pending = None
            continue
        if role == "user":
            pending = {"role": role, "content": content}
        elif role == "assistant" and pending is not None:
            pairs.append([pending, {"role": role, "content": content}])
            pending = None
        else:
            pending = None
    selected = []
    for pair in reversed(pairs[-max_pairs:] if max_pairs > 0 else []):
        candidate = pair + selected
        if len(json.dumps(candidate, ensure_ascii=False)) > max_chars:
            break
        selected = candidate
    return selected
