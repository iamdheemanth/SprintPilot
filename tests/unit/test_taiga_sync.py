from __future__ import annotations

import pytest

from tests.unit.fixtures.test_taiga_sprint_plan import make_taiga_sprint_plan

from sprintpilot.domain import Epic, Reasoning, SprintPlan, SprintStory, StoryPointEstimate, StoryTask
from sprintpilot.integrations.taiga.client import ExistingTaigaItem, MatchResult, TaigaClientProtocol
from sprintpilot.integrations.taiga.models import TaigaAuthMode, TaigaItemRef, TaigaSettings
from sprintpilot.integrations.taiga.sync import sync_sprint_plan_to_taiga


class RecordingTaigaClient(TaigaClientProtocol):
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.task_user_story_refs: list[int] = []
        self._next_id = 100

    def resolve_project(self, settings, auth):
        self.calls.append("resolve_project")
        from sprintpilot.integrations.taiga.models import TaigaProjectRef

        return TaigaProjectRef(identifier=settings.project_identifier, project_id=42)

    def find_existing_epic(self, project, source_ref, title=None):
        self.calls.append(f"find_epic:{source_ref.source_id}")
        return MatchResult.no_match()

    def find_existing_user_story(self, project, source_ref, title=None):
        self.calls.append(f"find_story:{source_ref.source_id}")
        return MatchResult.no_match()

    def find_existing_task(self, project, user_story_ref, source_ref, subject=None):
        self.calls.append(f"find_task:{source_ref.source_id}")
        return MatchResult.no_match()

    def create_epic(self, payload):
        self.calls.append(f"create_epic:{payload.source_ref.source_id}")
        self._next_id += 1
        return TaigaItemRef(item_type="epic", item_id=self._next_id, subject=payload.subject)

    def create_user_story(self, payload):
        self.calls.append(f"create_story:{payload.source_ref.source_id}")
        self._next_id += 1
        return TaigaItemRef(item_type="user_story", item_id=self._next_id, subject=payload.subject)

    def create_task(self, payload):
        self.calls.append(f"create_task:{payload.source_ref.source_id}")
        self.task_user_story_refs.append(payload.user_story_ref)
        self._next_id += 1
        return TaigaItemRef(item_type="task", item_id=self._next_id, subject=payload.subject)


def _settings() -> TaigaSettings:
    return TaigaSettings(
        base_url="https://taiga.example.com",
        project_identifier="project",
        auth_mode=TaigaAuthMode.BEARER,
        token_environment_key="SPRINTPILOT_TAIGA_TOKEN",
    )


def test_dry_run_returns_preview_without_client_mutations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-token")
    client = RecordingTaigaClient()

    result = sync_sprint_plan_to_taiga(
        make_taiga_sprint_plan(),
        settings=_settings(),
        client=client,
        dry_run=True,
    )

    assert result.dry_run is True
    assert len(result.previewed) == 4
    assert result.created == []
    assert client.calls == []


def test_write_mode_creates_epics_stories_then_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-token")
    client = RecordingTaigaClient()

    result = sync_sprint_plan_to_taiga(
        make_taiga_sprint_plan(),
        settings=_settings(),
        client=client,
        dry_run=False,
    )

    assert [item.item_type for item in result.created] == ["epic", "user_story", "task", "task"]
    assert client.calls.index("create_epic:EPIC-001") < client.calls.index("create_story:SP-001")
    assert client.calls.index("create_story:SP-001") < client.calls.index("create_task:TASK-001")
    assert client.task_user_story_refs == [102, 102]


def test_sync_matches_existing_items_by_source_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-token")
    client = RecordingTaigaClient()

    def existing_story(project, source_ref, title=None):
        return MatchResult.matched(
            ExistingTaigaItem(
                ref=TaigaItemRef(item_type="user_story", item_id=777, subject=title or ""),
                reason="Matched SprintPilot source id.",
            )
        )

    client.find_existing_user_story = existing_story  # type: ignore[method-assign]

    result = sync_sprint_plan_to_taiga(
        make_taiga_sprint_plan(),
        settings=_settings(),
        client=client,
        dry_run=False,
    )

    assert any(item.item_type == "user_story" and item.item_id == 777 for item in result.matched)
    assert "create_story:SP-001" not in client.calls
    assert client.task_user_story_refs == [777, 777]


def test_sync_skips_ambiguous_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-token")
    client = RecordingTaigaClient()

    def ambiguous_epic(project, source_ref, title=None):
        return MatchResult.ambiguous("Multiple Taiga epics share this title.")

    client.find_existing_epic = ambiguous_epic  # type: ignore[method-assign]

    result = sync_sprint_plan_to_taiga(
        make_taiga_sprint_plan(),
        settings=_settings(),
        client=client,
        dry_run=False,
    )

    assert result.skipped[0].item_type == "epic"
    assert "Multiple Taiga epics" in result.skipped[0].reasoning
    assert "create_epic:EPIC-001" not in client.calls


def test_missing_config_stops_before_client_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-token")
    client = RecordingTaigaClient()

    result = sync_sprint_plan_to_taiga(
        make_taiga_sprint_plan(),
        settings=None,
        client=client,
        dry_run=False,
    )

    assert result.failed
    assert "Taiga settings are required" in result.failed[0].reasoning
    assert client.calls == []


def test_dry_run_reports_unsupported_mapping_before_client_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-token")
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
    client = RecordingTaigaClient()

    result = sync_sprint_plan_to_taiga(plan, settings=_settings(), client=client, dry_run=True)

    assert result.failed
    assert "SP-999" in result.failed[0].reasoning
    assert client.calls == []
