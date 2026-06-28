from __future__ import annotations

from sprintpilot.domain import (
    Assumption,
    Epic,
    PlanningDependency,
    Reasoning,
    Risk,
    SprintPlan,
    SprintStory,
    StoryPointEstimate,
    StoryTask,
)


def make_taiga_sprint_plan() -> SprintPlan:
    return SprintPlan(
        epics=[
            Epic(
                id="EPIC-001",
                title="Backlog Readiness",
                objective="Prepare execution backlog for the product team.",
            )
        ],
        stories=[
            SprintStory(
                id="SP-001",
                title="Capture application",
                priority="P1",
                acceptance_criteria=[
                    "Given a student has an application, when they save it, then the tracker records the stage.",
                    "Given a recruiter exists, when linked, then contact details are visible.",
                ],
            )
        ],
        tasks=[
            StoryTask(
                id="TASK-001",
                story_id="SP-001",
                description="Create application stage validation.",
            ),
            StoryTask(
                id="TASK-002",
                story_id="SP-001",
                description="Render recruiter contact summary.",
            ),
        ],
        story_point_estimates=[
            StoryPointEstimate(
                story_id="SP-001",
                points=5,
                reasoning="Moderate workflow with validation and UI handoff.",
            )
        ],
        dependencies=[
            PlanningDependency(
                description="Application stages must be defined before analytics are reviewed.",
                impacts=["SP-001"],
            )
        ],
        assumptions=[Assumption(text="A single Taiga project is the export target.")],
        risks=[Risk(description="Recruiter details may contain incomplete contact data.")],
        reasoning=Reasoning(
            summary="The plan prioritizes user-visible backlog value.",
            evidence=["SP-001 is required before later reporting work."],
        ),
    )
