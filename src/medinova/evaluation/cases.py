"""Load versioned evaluation cases without depending on a telemetry vendor."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    question: str
    expected_agents: tuple[str, ...]
    expected_tools: tuple[str, ...]
    answer_contains: tuple[str, ...]


def load_cases(path: Path) -> tuple[EvaluationCase, ...]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Evaluation dataset must use version 1.")
    items = data.get("cases")
    if not isinstance(items, list) or not items:
        raise ValueError("Evaluation dataset must contain cases.")

    cases = []
    ids = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each evaluation case must be an object.")
        case_id, question = item.get("id"), item.get("question")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in ids:
            raise ValueError("Evaluation case IDs must be unique and non-empty.")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"Evaluation case {case_id} needs a question.")
        fields = ("expected_agents", "expected_tools", "answer_contains")
        for field in fields:
            value = item.get(field)
            if not isinstance(value, list) or any(
                not isinstance(entry, str) or not entry.strip() for entry in value
            ):
                raise ValueError(f"Evaluation case {case_id} needs a string list: {field}.")
        cases.append(EvaluationCase(
            id=case_id,
            question=question,
            expected_agents=tuple(item["expected_agents"]),
            expected_tools=tuple(item["expected_tools"]),
            answer_contains=tuple(item["answer_contains"]),
        ))
        ids.add(case_id)
    return tuple(cases)
