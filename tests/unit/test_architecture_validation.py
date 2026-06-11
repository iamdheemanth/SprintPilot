from __future__ import annotations

from tests.unit.test_architect_adapter import _valid_architecture_payload

from sprintpilot.domain import ArchitecturePlan
from sprintpilot.validation.artifacts import validate_architecture_completeness


def test_architecture_completeness_accepts_required_review_sections() -> None:
    plan = ArchitecturePlan.model_validate(_valid_architecture_payload())

    errors = validate_architecture_completeness(plan)

    assert errors == []


def test_architecture_completeness_requires_tradeoffs_assumptions_open_questions_and_reasoning() -> None:
    payload = _valid_architecture_payload()
    payload["tradeoffs"] = []
    payload["assumptions"] = []
    payload["open_questions"] = []
    payload["reasoning"] = {"summary": "Architecture guidance."}
    plan = ArchitecturePlan.model_validate(payload)

    errors = validate_architecture_completeness(plan)

    assert "tradeoff" in " ".join(errors)
    assert "assumption" in " ".join(errors)
    assert "open question" in " ".join(errors)


def test_architecture_completeness_rejects_analytics_modules_in_generated_plan() -> None:
    payload = _valid_architecture_payload()
    payload["system_components"] = [
        {
            "name": "Backend API",
            "responsibility": "Calculate application analytics for the student dashboard.",
        }
    ]
    plan = ArchitecturePlan.model_validate(payload)

    errors = validate_architecture_completeness(plan)

    assert errors == ["architecture plan includes out-of-scope content: analytics"]


def test_architecture_completeness_rejects_deployment_concerns_in_generated_plan() -> None:
    payload = _valid_architecture_payload()
    payload["recommended_architecture"] = "Use deployment automation and production hosting for Core v1."
    plan = ArchitecturePlan.model_validate(payload)

    errors = validate_architecture_completeness(plan)

    assert errors == ["architecture plan includes out-of-scope content: deployment concerns"]
