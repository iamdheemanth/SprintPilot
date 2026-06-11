from __future__ import annotations

from tests.unit.test_architect_adapter import _valid_architecture_payload
from tests.unit.test_architect_prompts import _definition
from tests.unit.test_scrum_master_adapter import _valid_sprint_payload

from sprintpilot.domain import ArchitecturePlan, EngineeringConfidenceAssessment, SprintPlan
from sprintpilot.workflow.core import run_confidence_assessment_workflow


def test_confidence_workflow_returns_human_reviewable_assessment() -> None:
    assessment = run_confidence_assessment_workflow(
        product_definition=_definition(),
        architecture_plan=ArchitecturePlan.model_validate(_valid_architecture_payload()),
        sprint_plan=SprintPlan.model_validate(_valid_sprint_payload()),
    )

    assert isinstance(assessment, EngineeringConfidenceAssessment)
    assert assessment.overall_score >= 0
    assert assessment.factor_scores
    assert assessment.reasoning.summary
    assert assessment.review_required is True
