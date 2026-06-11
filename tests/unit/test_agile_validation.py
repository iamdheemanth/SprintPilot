from __future__ import annotations

from tests.unit.test_scrum_master_adapter import _valid_sprint_payload

from sprintpilot.domain import SprintPlan
from sprintpilot.validation.artifacts import validate_sprint_plan_completeness


def test_sprint_plan_validation_accepts_complete_agile_sections() -> None:
    plan = SprintPlan.model_validate(_valid_sprint_payload())

    errors = validate_sprint_plan_completeness(plan)

    assert errors == []


def test_sprint_plan_validation_requires_estimate_reasoning_and_story_links() -> None:
    payload = _valid_sprint_payload()
    payload["story_point_estimates"] = [{"story_id": "UNKNOWN", "points": 5, "reasoning": "TBD"}]
    payload["tasks"] = [{"id": "TASK-001", "story_id": "UNKNOWN", "description": "Do planning work."}]
    plan = SprintPlan.model_validate(payload)

    errors = validate_sprint_plan_completeness(plan)

    joined = " ".join(errors)
    assert "estimate reasoning" in joined
    assert "unknown story" in joined
