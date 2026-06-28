from __future__ import annotations

import pytest

from sprintpilot.domain import Reasoning, SprintPlan, SprintStory, StoryPointEstimate, StoryTask, Epic
from sprintpilot.integrations.taiga.mapper import MappingValidationError, map_sprint_plan_to_taiga
from sprintpilot.integrations.taiga.models import (
    TaigaEpicPayload,
    TaigaProjectRef,
    assert_no_scheduling_fields,
)


def test_rejects_prohibited_scheduling_fields_in_payload_data() -> None:
    with pytest.raises(ValueError) as exc_info:
        assert_no_scheduling_fields({"subject": "Story", "milestone": 100})

    assert "milestone" in str(exc_info.value)


def test_payload_model_rejects_extra_scheduling_field() -> None:
    with pytest.raises(ValueError) as exc_info:
        TaigaEpicPayload(
            subject="Epic",
            description="Backlog epic",
            project_id=1,
            source_ref={"artifact_type": "epic", "source_id": "E-1", "source_title": "Epic"},
            sprint=12,
        )

    assert "sprint" in str(exc_info.value)


def test_mapper_rejects_task_with_unknown_story_reference() -> None:
    plan = SprintPlan(
        epics=[Epic(id="EPIC-001", title="Backlog", objective="Create backlog.")],
        stories=[
            SprintStory(
                id="SP-001",
                title="Known story",
                priority="P1",
                acceptance_criteria=["Given a story, when mapped, then it is exported."],
            )
        ],
        tasks=[StoryTask(id="TASK-001", story_id="SP-999", description="Orphan task.")],
        story_point_estimates=[
            StoryPointEstimate(story_id="SP-001", points=3, reasoning="Small story.")
        ],
        reasoning=Reasoning(summary="Plan has an orphan task."),
    )

    with pytest.raises(MappingValidationError) as exc_info:
        map_sprint_plan_to_taiga(plan, project=TaigaProjectRef(identifier="project", project_id=1))

    assert "SP-999" in str(exc_info.value)
