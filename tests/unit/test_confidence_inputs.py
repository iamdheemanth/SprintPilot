from __future__ import annotations

from tests.unit.test_architect_adapter import _valid_architecture_payload
from tests.unit.test_architect_prompts import _definition
from tests.unit.test_scrum_master_adapter import _valid_sprint_payload

from sprintpilot.domain import ArchitecturePlan, SprintPlan
from sprintpilot.scoring import assess_engineering_confidence


def test_missing_critical_artifacts_cap_score_at_60() -> None:
    product_definition = _definition()

    assessment = assess_engineering_confidence(
        product_definition=product_definition,
        architecture_plan=None,
        sprint_plan=None,
    )

    assert assessment.overall_score <= 60
    assert any(cap.reason == "missing_critical_artifacts" for cap in assessment.score_caps)
    assert assessment.missing_information


def test_incomplete_upstream_artifacts_reduce_factor_scores() -> None:
    product_definition = _definition()
    architecture_plan = ArchitecturePlan.model_validate(_valid_architecture_payload())
    sprint_plan = SprintPlan.model_validate(_valid_sprint_payload())
    architecture_plan.tradeoffs.clear()
    sprint_plan.story_point_estimates[0].reasoning = "TBD"

    assessment = assess_engineering_confidence(
        product_definition=product_definition,
        architecture_plan=architecture_plan,
        sprint_plan=sprint_plan,
    )

    factors = {factor.key: factor.score for factor in assessment.factor_scores}
    assert factors["architecture_completeness"] < 90
    assert factors["delivery_risk"] < 90
