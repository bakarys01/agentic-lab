"""Model-call observations keep timing while omitting prompts and responses."""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

from medinova.agents import langchain_metrics
from medinova.agents.smolagents_metrics import TracedModel


class Span:
    def __init__(self):
        self.ended = False

    def end(self):
        self.ended = True


def test_smolagents_model_call_has_real_lifetime_without_content(monkeypatch):
    events = []
    span = Span()

    def start(name, kind, model=None):
        events.append(("start", name, kind, model))
        return span

    def finish(observation, *, status="ok"):
        events.append(("finish", status, observation))
        observation.end()

    monkeypatch.setattr("medinova.agents.smolagents_metrics.start_observation", start)
    monkeypatch.setattr("medinova.agents.smolagents_metrics.finish_observation", finish)

    class Model:
        model_id = "gpt-4o"

        def generate(self, messages):
            assert events == [("start", "model-concierge", "generation", "gpt-4o")]
            return "PRIVATE RESPONSE"

    wrapped = TracedModel(Model(), "concierge")
    assert wrapped.model_id == "gpt-4o"
    assert wrapped.generate(["PRIVATE PROMPT"]) == "PRIVATE RESPONSE"
    assert events[-1] == ("finish", "ok", span)
    assert span.ended
    assert "PRIVATE" not in repr(events)


def test_langchain_model_callback_ends_generation_after_call(monkeypatch):
    events = []
    span = Span()
    monkeypatch.setattr(
        langchain_metrics, "start_observation",
        lambda name, kind, model=None: events.append(("start", name, kind, model)) or span,
    )
    monkeypatch.setattr(
        langchain_metrics, "finish_observation",
        lambda observation, *, status="ok": events.append(("finish", status, observation)),
    )
    recorder = langchain_metrics.ToolCallRecorder(agent_name="policy", model="gpt-4o")
    run_id = uuid4()

    async def record():
        await recorder.on_chat_model_start(
            {"name": "PRIVATE MODEL"}, [["PRIVATE PROMPT"]], run_id=run_id
        )
        await recorder.on_llm_end(
            SimpleNamespace(generations=[["PRIVATE RESPONSE"]]), run_id=run_id
        )

    asyncio.run(record())
    assert events == [
        ("start", "model-policy", "generation", "gpt-4o"),
        ("finish", "ok", span),
    ]
