from __future__ import annotations

from sprintpilot.integrations.taiga.auth import resolve_taiga_auth
from sprintpilot.integrations.taiga.client import TaigaClient
from sprintpilot.integrations.taiga.models import (
    SprintPilotSourceRef,
    TaigaAuthMode,
    TaigaEpicPayload,
    TaigaProjectRef,
    TaigaSettings,
)


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None, dict | None]] = []
        self.responses: list[object] = []

    def __call__(self, method: str, path: str, *, params=None, json_data=None, headers=None):
        self.calls.append((method, path, params, json_data))
        return self.responses.pop(0)


def _settings() -> TaigaSettings:
    return TaigaSettings(
        base_url="https://taiga.example.com",
        project_identifier="project-slug",
        auth_mode=TaigaAuthMode.BEARER,
        token_environment_key="SPRINTPILOT_TAIGA_TOKEN",
    )


def test_taiga_client_resolves_project_by_slug(monkeypatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-token")
    transport = RecordingTransport()
    transport.responses.append({"id": 42, "name": "Project", "slug": "project-slug"})
    settings = _settings()

    project = TaigaClient(settings=settings, auth=resolve_taiga_auth(settings), transport=transport).resolve_project(
        settings,
        resolve_taiga_auth(settings),
    )

    assert project.project_id == 42
    assert project.slug == "project-slug"
    assert transport.calls[0][0:3] == ("GET", "/api/v1/projects/by_slug", {"slug": "project-slug"})


def test_taiga_client_creates_epic_with_backlog_payload(monkeypatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-token")
    transport = RecordingTransport()
    transport.responses.append({"id": 101, "subject": "Backlog epic"})
    settings = _settings()
    source_ref = SprintPilotSourceRef(
        artifact_type="epic",
        source_id="EPIC-001",
        source_title="Backlog epic",
    )

    ref = TaigaClient(settings=settings, auth=resolve_taiga_auth(settings), transport=transport).create_epic(
        TaigaEpicPayload(
            project_id=42,
            subject="Backlog epic",
            description="SprintPilot-Source: epic:EPIC-001",
            source_ref=source_ref,
        )
    )

    assert ref.item_id == 101
    assert transport.calls[0][0:2] == ("POST", "/api/v1/epics")
    assert transport.calls[0][3] == {
        "project": 42,
        "subject": "Backlog epic",
        "description": "SprintPilot-Source: epic:EPIC-001",
    }


def test_taiga_client_matches_existing_epic_by_source_marker(monkeypatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-token")
    transport = RecordingTransport()
    transport.responses.append(
        [
            {
                "id": 101,
                "subject": "Backlog epic",
                "description": "SprintPilot-Source: epic:EPIC-001",
            }
        ]
    )
    settings = _settings()
    source_ref = SprintPilotSourceRef(
        artifact_type="epic",
        source_id="EPIC-001",
        source_title="Backlog epic",
    )

    result = TaigaClient(
        settings=settings,
        auth=resolve_taiga_auth(settings),
        transport=transport,
    ).find_existing_epic(TaigaProjectRef(identifier="project-slug", project_id=42), source_ref)

    assert result.is_match
    assert result.matched_item is not None
    assert result.matched_item.ref.item_id == 101
