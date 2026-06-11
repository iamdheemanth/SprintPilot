from __future__ import annotations

from sprintpilot.agents.adapters import parse_architecture_plan_result
from sprintpilot.llm import LLMResponse, StructuredGenerationResult


def _valid_architecture_payload() -> dict[str, object]:
    return {
        "recommended_architecture": "A modular local CLI with separate domain and orchestration layers.",
        "technology_stack_categories": [
            {"name": "Interface", "recommendation": "CLI", "rationale": "Smallest useful surface."}
        ],
        "system_components": [
            {
                "name": "Workflow Service",
                "responsibility": "Coordinate Product Manager and Architect stages.",
            }
        ],
        "database_considerations": "No database required for Core v1.",
        "tradeoffs": [
            {
                "decision": "Use local Markdown outputs.",
                "benefit": "Readable and simple.",
                "cost": "No cross-run project history.",
            }
        ],
        "assumptions": [{"text": "The user runs SprintPilot locally."}],
        "open_questions": [{"question": "Which model provider is configured?", "impact": "Affects setup."}],
        "risks": [{"description": "Generated architecture may miss constraints."}],
        "reasoning": {"summary": "Recommendation keeps Core v1 modular and local."},
    }


def test_parse_architecture_plan_result_returns_domain_model() -> None:
    result = StructuredGenerationResult(
        data=_valid_architecture_payload(),
        raw_response=LLMResponse(content="{}"),
    )

    parsed = parse_architecture_plan_result(result)

    assert parsed.is_valid is True
    assert parsed.recommended_architecture.startswith("A modular local CLI")


def test_parse_architecture_plan_result_reports_invalid_payload() -> None:
    result = StructuredGenerationResult(
        data={"recommended_architecture": "Incomplete"},
        raw_response=LLMResponse(content="{}"),
    )

    parsed = parse_architecture_plan_result(result)

    assert parsed.is_valid is False
    assert parsed.validation_errors


def test_parse_architecture_plan_result_rejects_out_of_scope_generated_work() -> None:
    payload = _valid_architecture_payload()
    payload["system_components"] = [
        {"name": "GitHub Bot", "responsibility": "Open GitHub pull requests automatically."}
    ]
    result = StructuredGenerationResult(data=payload, raw_response=LLMResponse(content="{}"))

    parsed = parse_architecture_plan_result(result)

    assert parsed.is_valid is False
    assert "GitHub integration" in parsed.validation_errors[0]


def test_parse_architecture_plan_result_rejects_generated_analytics_scope() -> None:
    payload = _valid_architecture_payload()
    payload["system_components"] = [
        {
            "name": "Application Analytics Module",
            "responsibility": "Provide metrics dashboards for application analytics.",
        }
    ]
    result = StructuredGenerationResult(data=payload, raw_response=LLMResponse(content="{}"))

    parsed = parse_architecture_plan_result(result)

    assert parsed.is_valid is False
    assert parsed.validation_errors == ["Architecture plan includes out-of-scope content: analytics"]


def test_parse_architecture_plan_result_rejects_generated_deployment_scope() -> None:
    payload = _valid_architecture_payload()
    payload["tradeoffs"] = [
        {
            "decision": "Add deployment pipeline.",
            "benefit": "Production hosting is automated.",
            "cost": "Introduces release engineering into Core v1.",
        }
    ]
    result = StructuredGenerationResult(data=payload, raw_response=LLMResponse(content="{}"))

    parsed = parse_architecture_plan_result(result)

    assert parsed.is_valid is False
    assert "deployment concerns" in parsed.validation_errors[0]
