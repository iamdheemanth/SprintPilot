from __future__ import annotations

import pytest
from pydantic import ValidationError

from sprintpilot.domain import (
    Assumption,
    PlanningDependency,
    Reasoning,
    Risk,
    SprintPlan,
    SprintStory,
    StoryPointEstimate,
    StoryTask,
    Epic,
)


def test_sprint_plan_requires_epics_stories_tasks_and_estimates() -> None:
    with pytest.raises(ValidationError):
        SprintPlan(
            epics=[],
            stories=[],
            tasks=[],
            story_point_estimates=[],
            reasoning=Reasoning(summary="Sprint plan."),
        )


def test_sprint_plan_preserves_agile_planning_sections() -> None:
    plan = SprintPlan(
        epics=[Epic(id="EPIC-001", title="Product Planning", objective="Clarify delivery scope.")],
        stories=[
            SprintStory(
                id="SP-001",
                title="Capture product idea",
                priority="P1",
                acceptance_criteria=["Given an idea, when planned, then requirements are produced."],
            )
        ],
        tasks=[
            StoryTask(id="TASK-001", story_id="SP-001", description="Validate product idea input.")
        ],
        story_point_estimates=[
            StoryPointEstimate(story_id="SP-001", points=3, reasoning="Small input workflow.")
        ],
        dependencies=[
            PlanningDependency(description="Product idea must exist before planning.", impacts=["SP-001"])
        ],
        assumptions=[Assumption(text="The user is planning one product idea.")],
        risks=[Risk(description="Story scope may be unclear.")],
        reasoning=Reasoning(summary="The plan is ordered by Agile value."),
    )

    assert plan.review_required is True
    assert plan.story_point_estimates[0].points == 3
