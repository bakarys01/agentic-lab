import json
from pathlib import Path

import pytest

from medinova.evaluation.cases import EvaluationCase, load_cases
from medinova.evaluation.grading import grade_case
from medinova.evaluation.runner import evaluate


def test_versioned_cases_load():
    cases = load_cases(Path("evaluation/cases/v1.json"))
    assert {case.id for case in cases} == {"policy_deductible", "medication_substance"}


def test_duplicate_ids_rejected(tmp_path):
    case = {"id": "same", "question": "Question?", "expected_agents": [],
            "expected_tools": [], "answer_contains": []}
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"version": 1, "cases": [case, case]}), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        load_cases(path)


def test_grade_reports_missing_routing_tools_and_facts():
    case = EvaluationCase("sample", "Question?", ("policy",),
                          ("search_policy",), ("déductible",))
    result = grade_case(case, "No answer", set(), set())
    assert result.failures == (
        "missing_agent:policy", "missing_tool:search_policy",
        "missing_answer_fact:déductible",
    )


def test_grade_accepts_accent_variants():
    case = EvaluationCase("sample", "Question?", ("medication",),
                          ("get_medication",), ("oxcarbazépine",))
    result = grade_case(case, "Substance : oxcarbazepine", {"medication"},
                        {"get_medication"})
    assert result.passed


def test_runner_keeps_answers_out_of_report():
    case = EvaluationCase("sample", "Secret question", ("policy",),
                          ("search_policy",), ("1,700",))
    payload = {
        "answer": "Your deductible is $1,700. Private answer text.",
        "agents_used": ["policy"],
        "metrics": [{"input_tokens": 10, "output_tokens": 5,
                     "tools": [{"name": "search_policy"}]}],
    }
    report = evaluate((case,), lambda question: payload)
    assert report["passed"] == 1
    assert report["results"][0]["tokens"] == 15
    assert "Private answer text" not in json.dumps(report)
