from __future__ import annotations

import pytest

from sprintpilot.config import RuntimeSettings
from sprintpilot.integrations.taiga.models import TaigaAuthMode, TaigaSettings


def test_taiga_settings_parse_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_BASE_URL", "https://taiga.example.com/")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_PROJECT", "project-slug")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_AUTH_MODE", "bearer")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN_ENV_KEY", "SPRINTPILOT_TAIGA_TOKEN")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_DRY_RUN", "true")

    settings = TaigaSettings.from_env()

    assert settings.base_url == "https://taiga.example.com"
    assert settings.project_identifier == "project-slug"
    assert settings.auth_mode is TaigaAuthMode.BEARER
    assert settings.token_environment_key == "SPRINTPILOT_TAIGA_TOKEN"
    assert settings.dry_run is True


def test_runtime_settings_include_optional_taiga_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "stub")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "stub-model")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_BASE_URL", "https://taiga.example.com")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_PROJECT", "project")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_AUTH_MODE", "application-token")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN_ENV_KEY", "SPRINTPILOT_TAIGA_TOKEN")

    settings = RuntimeSettings.from_env()

    assert settings.taiga is not None
    assert settings.taiga.auth_mode is TaigaAuthMode.APPLICATION_TOKEN


def test_runtime_settings_leave_taiga_unset_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "stub")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "stub-model")
    for key in (
        "SPRINTPILOT_TAIGA_BASE_URL",
        "SPRINTPILOT_TAIGA_PROJECT",
        "SPRINTPILOT_TAIGA_AUTH_MODE",
        "SPRINTPILOT_TAIGA_TOKEN_ENV_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = RuntimeSettings.from_env()

    assert settings.taiga is None


@pytest.mark.parametrize(
    ("missing_key", "expected_message"),
    [
        ("SPRINTPILOT_TAIGA_BASE_URL", "SPRINTPILOT_TAIGA_BASE_URL"),
        ("SPRINTPILOT_TAIGA_PROJECT", "SPRINTPILOT_TAIGA_PROJECT"),
        ("SPRINTPILOT_TAIGA_AUTH_MODE", "SPRINTPILOT_TAIGA_AUTH_MODE"),
        ("SPRINTPILOT_TAIGA_TOKEN_ENV_KEY", "SPRINTPILOT_TAIGA_TOKEN_ENV_KEY"),
    ],
)
def test_taiga_settings_report_missing_required_values(
    monkeypatch: pytest.MonkeyPatch,
    missing_key: str,
    expected_message: str,
) -> None:
    values = {
        "SPRINTPILOT_TAIGA_BASE_URL": "https://taiga.example.com",
        "SPRINTPILOT_TAIGA_PROJECT": "project",
        "SPRINTPILOT_TAIGA_AUTH_MODE": "bearer",
        "SPRINTPILOT_TAIGA_TOKEN_ENV_KEY": "SPRINTPILOT_TAIGA_TOKEN",
    }
    for key, value in values.items():
        if key == missing_key:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)

    with pytest.raises(ValueError) as exc_info:
        TaigaSettings.from_env(require=True)

    assert expected_message in str(exc_info.value)
