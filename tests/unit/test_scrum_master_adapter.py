from __future__ import annotations

from sprintpilot.agents.adapters import parse_sprint_plan_result
from sprintpilot.llm import LLMResponse, StructuredGenerationResult


def _valid_sprint_payload() -> dict[str, object]:
    return {
        "epics": [
            {"id": "EPIC-001", "title": "Planning Workflow", "objective": "Clarify product scope."}
        ],
        "stories": [
            {
                "id": "SP-001",
                "title": "Generate product definition",
                "priority": "P1",
                "acceptance_criteria": [
                    "Given a product idea, when planning runs, then a product definition is produced."
                ],
            }
        ],
        "tasks": [
            {"id": "TASK-001", "story_id": "SP-001", "description": "Validate product idea input."}
        ],
        "story_point_estimates": [
            {"story_id": "SP-001", "points": 3, "reasoning": "Small workflow with clear scope."}
        ],
        "dependencies": [
            {"description": "Product idea exists before planning.", "impacts": ["SP-001"]}
        ],
        "assumptions": [{"text": "The first release handles one product idea."}],
        "risks": [{"description": "Input ambiguity may affect story quality."}],
        "reasoning": {"summary": "Stories are ordered by Core v1 workflow value."},
    }


def test_parse_sprint_plan_result_returns_domain_model() -> None:
    result = StructuredGenerationResult(data=_valid_sprint_payload(), raw_response=LLMResponse(content="{}"))

    parsed = parse_sprint_plan_result(result)

    assert parsed.is_valid is True
    assert parsed.epics[0].id == "EPIC-001"


def test_parse_sprint_plan_result_reports_invalid_payload() -> None:
    result = StructuredGenerationResult(data={"epics": []}, raw_response=LLMResponse(content="{}"))

    parsed = parse_sprint_plan_result(result)

    assert parsed.is_valid is False
    assert parsed.validation_errors


def test_parse_sprint_plan_result_rejects_out_of_scope_generated_work() -> None:
    payload = _valid_sprint_payload()
    payload["tasks"] = [
        {"id": "TASK-001", "story_id": "SP-001", "description": "Open a GitHub pull request."}
    ]
    result = StructuredGenerationResult(data=payload, raw_response=LLMResponse(content="{}"))

    parsed = parse_sprint_plan_result(result)

    assert parsed.is_valid is False
    assert "GitHub integration" in parsed.validation_errors[0]
