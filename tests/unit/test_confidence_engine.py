from __future__ import annotations

from tests.unit.test_architect_adapter import _valid_architecture_payload
from tests.unit.test_architect_prompts import _definition
from tests.unit.test_scrum_master_adapter import _valid_sprint_payload

from sprintpilot.domain import ArchitecturePlan, SprintPlan
from sprintpilot.scoring import CONFIDENCE_FACTORS, assess_engineering_confidence


def _artifacts() -> tuple[object, ArchitecturePlan, SprintPlan]:
    return (
        _definition(),
        ArchitecturePlan.model_validate(_valid_architecture_payload()),
        SprintPlan.model_validate(_valid_sprint_payload()),
    )


def test_confidence_factor_weights_total_100() -> None:
    assert sum(factor.weight for factor in CONFIDENCE_FACTORS) == 100
    assert [factor.key for factor in CONFIDENCE_FACTORS] == [
        "requirement_clarity",
        "architecture_completeness",
        "dependency_readiness",
        "acceptance_criteria_quality",
        "technical_ambiguity",
        "delivery_risk",
    ]


def test_confidence_assessment_includes_factor_level_reasoning() -> None:
    product_definition, architecture_plan, sprint_plan = _artifacts()

    assessment = assess_engineering_confidence(
        product_definition=product_definition,
        architecture_plan=architecture_plan,
        sprint_plan=sprint_plan,
    )

    assert 0 <= assessment.overall_score <= 100
    assert len(assessment.factor_scores) == 6
    assert all(factor.reasoning for factor in assessment.factor_scores)
    assert assessment.review_required is True


def test_confidence_score_caps_when_out_of_scope_content_is_detected() -> None:
    product_definition, architecture_plan, sprint_plan = _artifacts()
    sprint_plan.tasks[0].description = "Open a GitHub pull request."

    assessment = assess_engineering_confidence(
        product_definition=product_definition,
        architecture_plan=architecture_plan,
        sprint_plan=sprint_plan,
    )

    assert assessment.overall_score <= 70
    assert any(cap.reason == "out_of_scope_content" for cap in assessment.score_caps)
    assert any("scope" in recommendation.action.lower() for recommendation in assessment.recommendations)
