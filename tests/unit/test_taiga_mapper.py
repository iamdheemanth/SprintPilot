from __future__ import annotations

from tests.unit.fixtures.test_taiga_sprint_plan import make_taiga_sprint_plan

from sprintpilot.integrations.taiga.mapper import map_sprint_plan_to_taiga
from sprintpilot.integrations.taiga.models import TaigaProjectRef


def test_maps_sprint_plan_epics_to_taiga_backlog_payloads() -> None:
    project = TaigaProjectRef(identifier="project", project_id=42, name="Project")

    mapped = map_sprint_plan_to_taiga(make_taiga_sprint_plan(), project=project)

    epic = mapped.epics[0]
    assert epic.subject == "Backlog Readiness"
    assert epic.project_id == 42
    assert "Prepare execution backlog" in epic.description
    assert "SprintPilot-Source: epic:EPIC-001" in epic.description
    assert not epic.contains_scheduling_fields()


def test_maps_sprint_plan_stories_with_acceptance_criteria_and_estimate_reasoning() -> None:
    project = TaigaProjectRef(identifier="project", project_id=42)

    mapped = map_sprint_plan_to_taiga(make_taiga_sprint_plan(), project=project)

    story = mapped.user_stories[0]
    assert story.subject == "Capture application"
    assert story.project_id == 42
    assert "Acceptance Criteria" in story.description
    assert "Given a student has an application" in story.description
    assert "Story Points: 5" in story.description
    assert "Moderate workflow" in story.description
    assert "SprintPilot-Source: story:SP-001" in story.description
    assert not story.contains_scheduling_fields()


def test_maps_sprint_plan_tasks_to_one_user_story_payload() -> None:
    project = TaigaProjectRef(identifier="project", project_id=42)

    mapped = map_sprint_plan_to_taiga(make_taiga_sprint_plan(), project=project)

    task = mapped.tasks[0]
    assert task.subject == "Create application stage validation."
    assert task.user_story_source_id == "SP-001"
    assert "SprintPilot-Source: task:TASK-001" in task.description
    assert not task.contains_scheduling_fields()
    assert task.with_user_story_ref(99).to_create_payload()["user_story"] == 99


def test_payload_dicts_exclude_scheduling_fields() -> None:
    project = TaigaProjectRef(identifier="project", project_id=42)

    mapped = map_sprint_plan_to_taiga(make_taiga_sprint_plan(), project=project)
    payloads = [*mapped.epics, *mapped.user_stories, *mapped.tasks]

    prohibited = {"sprint", "milestone", "capacity", "velocity", "sprint_order"}
    for payload in mapped.epics:
        assert prohibited.isdisjoint(payload.to_create_payload().keys())
    for payload in mapped.user_stories:
        assert prohibited.isdisjoint(payload.to_create_payload().keys())
    for payload in mapped.tasks:
        assert prohibited.isdisjoint(payload.with_user_story_ref(99).to_create_payload().keys())
