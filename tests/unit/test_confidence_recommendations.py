from __future__ import annotations

from tests.unit.test_architect_adapter import _valid_architecture_payload
from tests.unit.test_architect_prompts import _definition
from tests.unit.test_scrum_master_adapter import _valid_sprint_payload

from sprintpilot.domain import ArchitecturePlan, SprintPlan
from sprintpilot.scoring import assess_engineering_confidence


def test_low_confidence_scores_include_actionable_recommendations() -> None:
    product_definition = _definition()
    architecture_plan = ArchitecturePlan.model_validate(_valid_architecture_payload())
    sprint_plan = SprintPlan.model_validate(_valid_sprint_payload())
    product_definition.missing_information.clear()
    architecture_plan.open_questions.clear()
    sprint_plan.dependencies.clear()

    assessment = assess_engineering_confidence(
        product_definition=product_definition,
        architecture_plan=architecture_plan,
        sprint_plan=sprint_plan,
    )

    assert assessment.overall_score < 90
    assert assessment.recommendations
    assert all(recommendation.rationale for recommendation in assessment.recommendations)
