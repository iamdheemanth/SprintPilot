from __future__ import annotations

import pytest

from sprintpilot.integrations.taiga.auth import resolve_taiga_auth
from sprintpilot.integrations.taiga.models import TaigaAuthMode, TaigaSettings


def test_resolves_bearer_auth_header_without_exposing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-token")
    settings = TaigaSettings(
        base_url="https://taiga.example.com",
        project_identifier="project",
        auth_mode=TaigaAuthMode.BEARER,
        token_environment_key="SPRINTPILOT_TAIGA_TOKEN",
    )

    auth = resolve_taiga_auth(settings)

    assert auth.headers == {"Authorization": "Bearer secret-token"}
    assert "secret-token" not in repr(auth)
    assert "secret-token" not in str(auth.model_dump())


def test_resolves_application_token_auth_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "application-token")
    settings = TaigaSettings(
        base_url="https://taiga.example.com",
        project_identifier="project",
        auth_mode=TaigaAuthMode.APPLICATION_TOKEN,
        token_environment_key="SPRINTPILOT_TAIGA_TOKEN",
        username_or_email="user@example.com",
    )

    auth = resolve_taiga_auth(settings)

    assert auth.headers == {"Authorization": "Application application-token"}
    assert auth.identity == "user@example.com"


def test_missing_token_environment_value_reports_key_not_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPRINTPILOT_TAIGA_TOKEN", raising=False)
    settings = TaigaSettings(
        base_url="https://taiga.example.com",
        project_identifier="project",
        auth_mode=TaigaAuthMode.BEARER,
        token_environment_key="SPRINTPILOT_TAIGA_TOKEN",
    )

    with pytest.raises(ValueError) as exc_info:
        resolve_taiga_auth(settings)

    message = str(exc_info.value)
    assert "SPRINTPILOT_TAIGA_TOKEN" in message
    assert "secret" not in message.lower()
