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


def test_parse_product_definition_result_allows_single_student_internship_tracker_with_analytics() -> None:
    payload = _valid_payload()
    payload["summary"] = (
        "A student internship tracker for an individual student with application analytics "
        "for their own applications."
    )
    payload["primary_users"] = ["students"]
    payload["functional_requirements"] = [
        {"id": "FR-001", "text": "System must let a student track internship applications."},
        {
            "id": "FR-002",
            "text": "System must show application analytics for the student's own application pipeline.",
        },
    ]
    payload["user_stories"] = [
        {
            "id": "US-001",
            "title": "Track own application analytics",
            "priority": "P1",
            "actor": "student",
            "goal": "review my application analytics",
            "benefit": "understand my own internship search progress",
            "acceptance_criteria": [
                {
                    "given": "my tracked applications",
                    "when": "I view analytics",
                    "then": "I see insights about my own application statuses",
                }
            ],
        }
    ]
    result = StructuredGenerationResult(
        data=payload,
        raw_response=LLMResponse(content="{}"),
    )

    parsed = parse_product_definition_result(result)

    assert parsed.is_valid is True
    assert parsed.primary_users == ["students"]


def test_parse_product_definition_result_accepts_exact_internship_tracker_idea_with_personal_analytics() -> None:
    payload = _valid_payload()
    payload["summary"] = (
        "A single-student internship tracking platform that helps a student track applications, "
        "interview stages, offers, deadlines, recruiter contacts and application analytics."
    )
    payload["primary_users"] = ["students"]
    payload["functional_requirements"] = [
        {"id": "FR-001", "text": "System must let the student track internship applications."},
        {"id": "FR-002", "text": "System must let the student track interview stages and offers."},
        {"id": "FR-003", "text": "System must track deadlines and recruiter contacts."},
        {
            "id": "FR-004",
            "text": (
                "System must show personal application analytics including total applications, "
                "applications by status, interview and offer counts, and upcoming deadline summary."
            ),
        },
    ]
    result = StructuredGenerationResult(
        data=payload,
        raw_response=LLMResponse(content="{}"),
    )

    parsed = parse_product_definition_result(result)

    assert parsed.is_valid is True
    assert parsed.summary.startswith("A single-student internship tracking platform")


def test_parse_product_definition_result_rejects_collaboration_features() -> None:
    payload = _valid_payload()
    payload["functional_requirements"] = [
        {
            "id": "FR-001",
            "text": "System must let students share applications in a shared workspace.",
        },
        {
            "id": "FR-002",
            "text": "System must support advisor comments and co-editing application notes.",
        },
    ]
    result = StructuredGenerationResult(
        data=payload,
        raw_response=LLMResponse(content="{}"),
    )

    parsed = parse_product_definition_result(result)

    assert parsed.is_valid is False
    assert len(parsed.validation_errors) == 1
    error = parsed.validation_errors[0]
    assert "Product definition includes out-of-scope content: multi-user collaboration" in error
    assert "matched text 'shared workspace'" in error
    assert "field functional_requirements[0].text" in error


def test_parse_product_definition_result_reports_forbidden_text_and_field_path() -> None:
    payload = _valid_payload()
    payload["functional_requirements"] = [
        {
            "id": "FR-001",
            "text": "System must let students share applications in a shared workspace.",
        }
    ]
    result = StructuredGenerationResult(
        data=payload,
        raw_response=LLMResponse(content="{}"),
    )

    parsed = parse_product_definition_result(result)

    assert parsed.is_valid is False
    error = parsed.validation_errors[0]
    assert "multi-user collaboration" in error
    assert "matched text 'shared workspace'" in error
    assert "field functional_requirements[0].text" in error


def test_parse_product_definition_result_rejects_separate_analytics_dashboard_platform() -> None:
    payload = _valid_payload()
    payload["functional_requirements"] = [
        {
            "id": "FR-001",
            "text": "System must provide a standalone analytics dashboard for internship trends.",
        },
        {
            "id": "FR-002",
            "text": "System must include a reporting platform for application analytics.",
        },
    ]
    result = StructuredGenerationResult(
        data=payload,
        raw_response=LLMResponse(content="{}"),
    )

    parsed = parse_product_definition_result(result)

    assert parsed.is_valid is False
    assert len(parsed.validation_errors) == 1
    error = parsed.validation_errors[0]
    assert "Product definition includes out-of-scope content: analytics" in error
    assert "matched text 'analytics dashboard'" in error
    assert "field functional_requirements[0].text" in error
