"""Map SprintPilot SprintPlan artifacts to Taiga backlog payloads."""

from __future__ import annotations

from sprintpilot.domain import SprintPlan, SprintStory, StoryPointEstimate
from sprintpilot.integrations.taiga.models import (
    SprintPilotSourceRef,
    TaigaEpicPayload,
    TaigaMappedPayloads,
    TaigaProjectRef,
    TaigaTaskPayload,
    TaigaUserStoryPayload,
)


class MappingValidationError(ValueError):
    """Raised when SprintPlan data cannot be safely exported to Taiga backlog."""


def map_sprint_plan_to_taiga(
    sprint_plan: SprintPlan,
    *,
    project: TaigaProjectRef,
) -> TaigaMappedPayloads:
    """Convert a SprintPlan into Taiga backlog epics, user stories, and tasks."""

    story_ids = {story.id for story in sprint_plan.stories}
    orphan_tasks = [task for task in sprint_plan.tasks if task.story_id not in story_ids]
    if orphan_tasks:
        orphan_ids = ", ".join(f"{task.id}->{task.story_id}" for task in orphan_tasks)
        raise MappingValidationError(f"SprintPlan tasks reference unknown stories: {orphan_ids}")

    estimates_by_story = {
        estimate.story_id: estimate for estimate in sprint_plan.story_point_estimates
    }
    epics = [
        TaigaEpicPayload(
            project_id=project.project_id,
            subject=epic.title,
            description=_epic_description(epic.objective, epic.id, epic.title, sprint_plan),
            source_ref=SprintPilotSourceRef(
                artifact_type="epic",
                source_id=epic.id,
                source_title=epic.title,
            ),
        )
        for epic in sprint_plan.epics
    ]
    user_stories = [
        TaigaUserStoryPayload(
            project_id=project.project_id,
            subject=story.title,
            description=_story_description(story, estimates_by_story.get(story.id), sprint_plan),
            source_ref=SprintPilotSourceRef(
                artifact_type="story",
                source_id=story.id,
                source_title=story.title,
            ),
        )
        for story in sprint_plan.stories
    ]
    tasks = [
        TaigaTaskPayload(
            project_id=project.project_id,
            subject=task.description,
            description=_task_description(task.id, task.description, task.story_id),
            user_story_source_id=task.story_id,
            source_ref=SprintPilotSourceRef(
                artifact_type="task",
                source_id=task.id,
                source_title=task.description,
            ),
        )
        for task in sprint_plan.tasks
    ]
    return TaigaMappedPayloads(
        project=project,
        epics=epics,
        user_stories=user_stories,
        tasks=tasks,
    )


def _epic_description(objective: str, source_id: str, title: str, sprint_plan: SprintPlan) -> str:
    sections = [
        f"SprintPilot-Source: epic:{source_id}",
        "",
        "Objective",
        objective,
        "",
        "Planning Reasoning",
        sprint_plan.reasoning.summary,
    ]
    return "\n".join(sections)


def _story_description(
    story: SprintStory,
    estimate: StoryPointEstimate | None,
    sprint_plan: SprintPlan,
) -> str:
    sections = [
        f"SprintPilot-Source: story:{story.id}",
        "",
        f"Priority: {story.priority}",
        "",
        "Acceptance Criteria",
        *[f"- {criterion}" for criterion in story.acceptance_criteria],
    ]
    if estimate is not None:
        sections.extend(
            [
                "",
                f"Story Points: {estimate.points}",
                f"Estimate Reasoning: {estimate.reasoning}",
            ]
        )
    if sprint_plan.dependencies:
        sections.extend(["", "Dependencies"])
        sections.extend(
            f"- {dependency.description}"
            for dependency in sprint_plan.dependencies
            if not dependency.impacts or story.id in dependency.impacts
        )
    if sprint_plan.assumptions:
        sections.extend(["", "Assumptions"])
        sections.extend(f"- {assumption.text}" for assumption in sprint_plan.assumptions)
    if sprint_plan.risks:
        sections.extend(["", "Risks"])
        sections.extend(f"- {risk.description}" for risk in sprint_plan.risks)
    return "\n".join(sections)


def _task_description(task_id: str, description: str, story_id: str) -> str:
    return "\n".join(
        [
            f"SprintPilot-Source: task:{task_id}",
            "",
            f"Parent SprintPilot Story: {story_id}",
            "",
            description,
        ]
    )
