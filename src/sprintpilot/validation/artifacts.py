"""Cross-artifact validation helpers."""

from __future__ import annotations

from sprintpilot.domain import ArchitecturePlan, SprintPlan
from sprintpilot.validation.scope import detect_architecture_forbidden_scope


def validate_architecture_completeness(plan: ArchitecturePlan) -> list[str]:
    """Validate ArchitecturePlan sections that must remain reviewable."""

    errors: list[str] = []
    if not plan.tradeoffs:
        errors.append("architecture plan must include at least one tradeoff")
    if not plan.assumptions:
        errors.append("architecture plan must include at least one assumption")
    if not plan.open_questions:
        errors.append("architecture plan must include at least one open question")
    if not plan.reasoning.summary.strip():
        errors.append("architecture plan must include reasoning")
    findings = detect_architecture_forbidden_scope(plan.model_dump_json())
    if findings:
        labels = ", ".join(finding.label for finding in findings)
        errors.append(f"architecture plan includes out-of-scope content: {labels}")
    return errors


def validate_sprint_plan_completeness(plan: SprintPlan) -> list[str]:
    """Validate SprintPlan Agile sections and estimate reasoning."""

    errors: list[str] = []
    story_ids = {story.id for story in plan.stories}

    for task in plan.tasks:
        if task.story_id not in story_ids:
            errors.append(f"task {task.id} references unknown story {task.story_id}")

    for estimate in plan.story_point_estimates:
        if estimate.story_id not in story_ids:
            errors.append(f"estimate references unknown story {estimate.story_id}")
        if estimate.reasoning.strip().lower() in {"tbd", "todo", "none", "n/a"}:
            errors.append(f"estimate reasoning is required for story {estimate.story_id}")

    if not plan.dependencies:
        errors.append("sprint plan should include dependencies or explicitly explain none")
    if not plan.reasoning.summary.strip():
        errors.append("sprint plan must include reasoning")

    return errors
