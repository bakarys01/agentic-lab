from types import SimpleNamespace

import pytest

from medinova.backend import title_generation


def test_title_generation_uses_small_configured_model_and_bounded_input(monkeypatch):
    calls = []

    class FakeResponses:
        def parse(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(output_parsed=SimpleNamespace(title="  Sleep   apnea treatment  "))

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(title_generation, "OpenAI", lambda **kwargs: SimpleNamespace(responses=FakeResponses()))

    assert title_generation.generate_title("Q" * 2000, "A" * 2000) == "Sleep apnea treatment"
    assert calls[0]["model"] == "gpt-4o-mini"
    assert calls[0]["store"] is False
    assert calls[0]["input"].count("Q") == 1000
    assert calls[0]["input"].split("Assistant answer:\n", 1)[1] == "A" * 1000


def test_title_generation_rejects_invalid_output(monkeypatch):
    class FakeResponses:
        def parse(self, **kwargs):
            return SimpleNamespace(output_parsed=SimpleNamespace(title=" "))

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(title_generation, "OpenAI", lambda **kwargs: SimpleNamespace(responses=FakeResponses()))
    with pytest.raises(ValueError, match="invalid title"):
        title_generation.generate_title("Question", "Answer")
