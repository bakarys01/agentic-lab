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
