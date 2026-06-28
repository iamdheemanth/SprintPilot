from __future__ import annotations

from tests.unit.fixtures.test_taiga_sprint_plan import make_taiga_sprint_plan
from tests.unit.test_taiga_sync import RecordingTaigaClient

from sprintpilot.integrations.taiga.models import TaigaAuthMode, TaigaSettings
from sprintpilot.integrations.taiga.sync import sync_sprint_plan_to_taiga


def test_taiga_sync_workflow_uses_mocked_client_without_live_taiga(monkeypatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-token")

    result = sync_sprint_plan_to_taiga(
        make_taiga_sprint_plan(),
        settings=TaigaSettings(
            base_url="https://taiga.example.com",
            project_identifier="project",
            auth_mode=TaigaAuthMode.BEARER,
            token_environment_key="SPRINTPILOT_TAIGA_TOKEN",
        ),
        client=RecordingTaigaClient(),
        dry_run=False,
    )

    assert result.failed == []
    assert [item.item_type for item in result.created] == ["epic", "user_story", "task", "task"]
