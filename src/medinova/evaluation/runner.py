"""Run portable checks against the concierge without exporting chat contents."""

import argparse
import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from typing import Any

from medinova.evaluation.cases import EvaluationCase, load_cases
from medinova.evaluation.grading import grade_case


def evaluate(
    cases: tuple[EvaluationCase, ...],
    answer_case: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    results = []
    for case in cases:
        started = perf_counter()
        try:
            payload = answer_case(case.question)
            metrics = payload.get("metrics") or []
            if not isinstance(metrics, list):
                metrics = []
            tools = {
                tool["name"]
                for run in metrics if isinstance(run, dict)
                for tool in run.get("tools", [])
                if isinstance(tool, dict) and isinstance(tool.get("name"), str)
            }
            grade = grade_case(
                case,
                payload["answer"],
                set(payload.get("agents_used") or []),
                tools,
            )
            token_values = [
                run[key]
                for run in metrics if isinstance(run, dict)
                for key in ("input_tokens", "output_tokens")
                if isinstance(run.get(key), int)
            ]
            results.append({
                **asdict(grade),
                "duration_ms": int((perf_counter() - started) * 1000),
                "tokens": sum(token_values) if token_values else None,
            })
        except Exception as exc:
            results.append({
                "case_id": case.id,
                "passed": False,
                "failures": [f"execution_error:{type(exc).__name__}"],
                "duration_ms": int((perf_counter() - started) * 1000),
                "tokens": None,
            })
    return {
        "dataset_version": 1,
        "total": len(results),
        "passed": sum(result["passed"] for result in results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local MediNova evaluation cases.")
    parser.add_argument("--cases", type=Path, default=Path("evaluation/cases/v1.json"))
    parser.add_argument("--output", type=Path, help="Write a content-free JSON report.")
    args = parser.parse_args()

    from medinova.agents.config_loader import load_agent_definition
    from medinova.agents.runtime import AgentRuntime

    concierge = AgentRuntime(load_agent_definition("concierge"))
    report = evaluate(load_cases(args.cases), concierge.answer_query_with_metadata)
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)
    if report["passed"] != report["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
