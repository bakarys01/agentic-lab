"""Deterministic checks; passing them does not establish medical correctness."""

import unicodedata
from dataclasses import dataclass

from medinova.evaluation.cases import EvaluationCase


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    passed: bool
    failures: tuple[str, ...]


def _normalize(value: str) -> str:
    return "".join(
        character for character in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(character)
    )


def grade_case(
    case: EvaluationCase,
    answer: str,
    agents_used: set[str],
    tools_used: set[str],
) -> EvaluationResult:
    failures = []
    for agent in case.expected_agents:
        if agent not in agents_used:
            failures.append(f"missing_agent:{agent}")
    for tool in case.expected_tools:
        if tool not in tools_used:
            failures.append(f"missing_tool:{tool}")
    normalized_answer = _normalize(answer)
    for fact in case.answer_contains:
        if _normalize(fact) not in normalized_answer:
            failures.append(f"missing_answer_fact:{fact}")
    return EvaluationResult(case.id, not failures, tuple(failures))
