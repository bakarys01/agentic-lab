from types import SimpleNamespace

from agents.concierge_agent import ConciergeAgent
from agents.conversation_memory import recent_history


def pair(question, answer):
    return [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]


def test_history_keeps_last_six_complete_pairs():
    history = [message for n in range(10) for message in pair(f"question-{n}", f"answer-{n}")]
    selected = recent_history(history)
    assert len(selected) == 12
    assert selected[0]["content"] == "question-4"
    assert history[0]["content"] == "question-0"


def test_history_omits_failed_pending_or_unpaired_messages():
    history = [*pair("Valid", "Reply"), {"role": "user", "content": "failed", "status": "failed"},
               {"role": "assistant", "content": "orphan"},
               {"role": "user", "content": "pending", "status": "pending"}]
    assert recent_history(history) == pair("Valid", "Reply")


def test_history_is_bounded_and_excludes_system_roles():
    assert recent_history(pair("q", "a" * 16001)) == []
    assert recent_history([{"role": "system", "content": "bad"}, *pair("q", "a")]) == pair("q", "a")
    assert recent_history(pair("q", "a"), max_chars=1) == []


def test_context_is_passed_and_agent_state_reset_for_each_request():
    calls = []
    def run(task, **kwargs):
        calls.append((task, kwargs))
        return "Answer"
    concierge = ConciergeAgent.__new__(ConciergeAgent)
    concierge.agent = SimpleNamespace(run=run, memory=SimpleNamespace(steps=[]))
    concierge.answer_query_with_metadata("Is it covered?", history=pair("sleep apnea", "CPAP"))
    concierge.answer_query_with_metadata("New topic", history=[])
    assert "sleep apnea" in calls[0][0] and "CPAP" in calls[0][0]
    assert "sleep apnea" not in calls[1][0] and "CPAP" not in calls[1][0]
    assert all(kwargs["reset"] is True for _, kwargs in calls)


def test_cli_answer_also_resets_execution():
    concierge = ConciergeAgent.__new__(ConciergeAgent)
    concierge.agent = SimpleNamespace(run=lambda task, reset: str(reset))
    assert concierge.answer_query("Hello") == "True"
