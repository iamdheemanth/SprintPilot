from __future__ import annotations

from sprintpilot.agents.adapters import parse_product_definition_result
from sprintpilot.llm import LLMResponse, StructuredGenerationResult


def _valid_payload() -> dict[str, object]:
    return {
        "summary": "A planning assistant for founders.",
        "primary_users": ["founders"],
        "functional_requirements": [
            {"id": "FR-001", "text": "System must accept a product idea."}
        ],
        "non_functional_requirements": [
            {"id": "NFR-001", "text": "Outputs must include reasoning."}
        ],
        "user_stories": [
            {
                "id": "US-001",
                "title": "Capture idea",
                "priority": "P1",
                "actor": "founder",
                "goal": "enter a product idea",
                "benefit": "receive a product definition",
                "acceptance_criteria": [
                    {
                        "given": "a product idea",
                        "when": "planning is requested",
                        "then": "a product definition is generated",
                    }
                ],
            }
        ],
        "assumptions": [{"text": "The user is planning a small product."}],
        "missing_information": [{"question": "Who are the first users?", "impact": "Affects scope."}],
        "reasoning": {"summary": "The output focuses on ambiguity reduction."},
    }


def test_parse_product_definition_result_returns_domain_model() -> None:
    result = StructuredGenerationResult(
        data=_valid_payload(),
        raw_response=LLMResponse(content="{}"),
    )

    definition = parse_product_definition_result(result)

    assert definition.summary == "A planning assistant for founders."
    assert definition.functional_requirements[0].id == "FR-001"


def test_parse_product_definition_result_reports_invalid_payload() -> None:
    result = StructuredGenerationResult(
        data={"summary": "Incomplete"},
        raw_response=LLMResponse(content="{}"),
    )

    parsed = parse_product_definition_result(result)

    assert parsed.is_valid is False
    assert parsed.validation_errors


def test_parse_product_definition_result_rejects_out_of_scope_generated_work() -> None:
    payload = _valid_payload()
    payload["functional_requirements"] = [
        {"id": "FR-001", "text": "System must open GitHub pull requests."}
    ]
    result = StructuredGenerationResult(
        data=payload,
        raw_response=LLMResponse(content="{}"),
    )

    parsed = parse_product_definition_result(result)

    assert parsed.is_valid is False
    assert "GitHub integration" in parsed.validation_errors[0]


def test_parse_product_definition_result_allows_application_analytics_as_product_concept() -> None:
    payload = _valid_payload()
    payload["summary"] = "A student internship tracker with application analytics for students."
    payload["functional_requirements"] = [
        {
            "id": "FR-001",
            "text": "System must show application analytics for internship applications.",
        }
    ]
    result = StructuredGenerationResult(
        data=payload,
        raw_response=LLMResponse(content="{}"),
    )

    parsed = parse_product_definition_result(result)

    assert parsed.is_valid is True
    assert "application analytics" in parsed.summary
