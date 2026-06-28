from __future__ import annotations

from pathlib import Path

from sprintpilot.integrations.taiga.config import (
    TaigaConfigOverrides,
    resolve_taiga_settings,
)
from sprintpilot.integrations.taiga.models import TaigaAuthMode
from sprintpilot.integrations.taiga.profile_store import (
    RepoTaigaBindingStore,
    TaigaConnectionProfile,
    TaigaProfileStore,
)


def _save_profile(
    store: TaigaProfileStore,
    name: str,
    *,
    base_url: str,
    project: str,
    token_key: str,
    make_default: bool = False,
) -> None:
    store.save_profile(
        TaigaConnectionProfile(
            name=name,
            base_url=base_url,
            project_identifier=project,
            auth_mode="bearer",
            token_environment_key=token_key,
        ),
        make_default=make_default,
    )


def test_resolution_prefers_explicit_overrides_over_repo_binding(tmp_path: Path) -> None:
    profile_store = TaigaProfileStore(config_dir=tmp_path / "config")
    binding_store = RepoTaigaBindingStore(repo_dir=tmp_path / "repo")
    _save_profile(
        profile_store,
        "bound",
        base_url="https://bound.taiga.test",
        project="bound-project",
        token_key="BOUND_TOKEN",
    )
    binding_store.set_active_profile("bound")

    settings = resolve_taiga_settings(
        overrides=TaigaConfigOverrides(
            base_url="https://override.taiga.test",
            project_identifier="override-project",
            auth_mode="application-token",
            token_environment_key="OVERRIDE_TOKEN",
        ),
        profile_store=profile_store,
        binding_store=binding_store,
        env={},
    )

    assert settings.base_url == "https://override.taiga.test"
    assert settings.project_identifier == "override-project"
    assert settings.auth_mode is TaigaAuthMode.APPLICATION_TOKEN
    assert settings.token_environment_key == "OVERRIDE_TOKEN"


def test_complete_explicit_overrides_ignore_stale_repo_binding(tmp_path: Path) -> None:
    binding_store = RepoTaigaBindingStore(repo_dir=tmp_path / "repo")
    binding_store.set_active_profile("deleted-profile")

    settings = resolve_taiga_settings(
        overrides=TaigaConfigOverrides(
            base_url="https://override.taiga.test",
            project_identifier="override-project",
            auth_mode="bearer",
            token_environment_key="OVERRIDE_TOKEN",
        ),
        profile_store=TaigaProfileStore(config_dir=tmp_path / "config"),
        binding_store=binding_store,
        env={},
    )

    assert settings.base_url == "https://override.taiga.test"
    assert settings.project_identifier == "override-project"


def test_resolution_uses_repo_active_profile_before_user_default(tmp_path: Path) -> None:
    profile_store = TaigaProfileStore(config_dir=tmp_path / "config")
    binding_store = RepoTaigaBindingStore(repo_dir=tmp_path / "repo")
    _save_profile(
        profile_store,
        "default",
        base_url="https://default.taiga.test",
        project="default-project",
        token_key="DEFAULT_TOKEN",
        make_default=True,
    )
    _save_profile(
        profile_store,
        "repo",
        base_url="https://repo.taiga.test",
        project="repo-project",
        token_key="REPO_TOKEN",
    )
    binding_store.set_active_profile("repo")

    settings = resolve_taiga_settings(
        profile_store=profile_store,
        binding_store=binding_store,
        env={},
    )

    assert settings.base_url == "https://repo.taiga.test"
    assert settings.project_identifier == "repo-project"
    assert settings.token_environment_key == "REPO_TOKEN"


def test_resolution_uses_user_default_profile_before_legacy_environment(tmp_path: Path) -> None:
    profile_store = TaigaProfileStore(config_dir=tmp_path / "config")
    binding_store = RepoTaigaBindingStore(repo_dir=tmp_path / "repo")
    _save_profile(
        profile_store,
        "default",
        base_url="https://default.taiga.test",
        project="default-project",
        token_key="DEFAULT_TOKEN",
        make_default=True,
    )

    settings = resolve_taiga_settings(
        profile_store=profile_store,
        binding_store=binding_store,
        env={
            "SPRINTPILOT_TAIGA_BASE_URL": "https://legacy.taiga.test",
            "SPRINTPILOT_TAIGA_PROJECT": "legacy-project",
            "SPRINTPILOT_TAIGA_AUTH_MODE": "bearer",
            "SPRINTPILOT_TAIGA_TOKEN_ENV_KEY": "LEGACY_TOKEN",
        },
    )

    assert settings.base_url == "https://default.taiga.test"
    assert settings.project_identifier == "default-project"


def test_resolution_falls_back_to_legacy_environment(tmp_path: Path) -> None:
    settings = resolve_taiga_settings(
        profile_store=TaigaProfileStore(config_dir=tmp_path / "config"),
        binding_store=RepoTaigaBindingStore(repo_dir=tmp_path / "repo"),
        env={
            "SPRINTPILOT_TAIGA_BASE_URL": "https://legacy.taiga.test",
            "SPRINTPILOT_TAIGA_PROJECT": "legacy-project",
            "SPRINTPILOT_TAIGA_AUTH_MODE": "bearer",
            "SPRINTPILOT_TAIGA_TOKEN_ENV_KEY": "LEGACY_TOKEN",
        },
    )

    assert settings.base_url == "https://legacy.taiga.test"
    assert settings.project_identifier == "legacy-project"
