"""Taiga configuration resolution from overrides, profiles, and legacy env."""

from __future__ import annotations

from dataclasses import dataclass

from sprintpilot.integrations.taiga.models import TaigaAuthMode, TaigaSettings
from sprintpilot.integrations.taiga.profile_store import (
    RepoTaigaBindingStore,
    TaigaConnectionProfile,
    TaigaProfileStore,
)


@dataclass(frozen=True)
class TaigaConfigOverrides:
    """Explicit CLI configuration values that take precedence over profiles."""

    profile_name: str | None = None
    base_url: str | None = None
    project_identifier: str | None = None
    auth_mode: str | TaigaAuthMode | None = None
    token_environment_key: str | None = None
    token_reference: str | None = None
    username_or_email: str | None = None
    timeout_seconds: float | None = None
    max_retries: int | None = None
    dry_run: bool | None = None

    def has_any_value(self) -> bool:
        return any(value is not None for value in self.__dict__.values())


def resolve_taiga_settings(
    *,
    overrides: TaigaConfigOverrides | None = None,
    profile_store: TaigaProfileStore | None = None,
    binding_store: RepoTaigaBindingStore | None = None,
    env: dict[str, str] | None = None,
) -> TaigaSettings | None:
    """Resolve Taiga settings in product UX order."""

    overrides = overrides or TaigaConfigOverrides()
    profile_store = profile_store or TaigaProfileStore()
    binding_store = binding_store or RepoTaigaBindingStore()

    if overrides.profile_name is None and _has_complete_direct_overrides(overrides):
        return _settings_from_overrides(overrides)

    profile = _select_profile(overrides, profile_store, binding_store)
    if profile is not None:
        return _settings_from_profile(profile, overrides)

    if _has_complete_direct_overrides(overrides):
        return _settings_from_overrides(overrides)

    legacy = TaigaSettings.from_env(env)
    if legacy is None and overrides.has_any_value():
        return _settings_from_overrides(overrides)
    return legacy


def _select_profile(
    overrides: TaigaConfigOverrides,
    profile_store: TaigaProfileStore,
    binding_store: RepoTaigaBindingStore,
) -> TaigaConnectionProfile | None:
    if overrides.profile_name:
        profile = profile_store.get_profile(overrides.profile_name)
        if profile is None:
            raise ValueError(f"Taiga profile '{overrides.profile_name}' was not found")
        return profile
    active_name = binding_store.get_active_profile_name()
    if active_name:
        profile = profile_store.get_profile(active_name)
        if profile is None:
            raise ValueError(f"Repo Taiga profile '{active_name}' was not found")
        return profile
    default_name = profile_store.get_default_profile_name()
    if default_name:
        profile = profile_store.get_profile(default_name)
        if profile is None:
            raise ValueError(f"Default Taiga profile '{default_name}' was not found")
        return profile
    return None


def _settings_from_profile(
    profile: TaigaConnectionProfile,
    overrides: TaigaConfigOverrides,
) -> TaigaSettings:
    values = profile.model_dump(exclude={"name"}, exclude_none=True)
    values.update(_override_values(overrides))
    return TaigaSettings(**values)


def _settings_from_overrides(overrides: TaigaConfigOverrides) -> TaigaSettings:
    return TaigaSettings(**_override_values(overrides))


def _override_values(overrides: TaigaConfigOverrides) -> dict[str, object]:
    values = {
        "base_url": overrides.base_url,
        "project_identifier": overrides.project_identifier,
        "auth_mode": overrides.auth_mode,
        "token_environment_key": overrides.token_environment_key,
        "token_reference": overrides.token_reference,
        "username_or_email": overrides.username_or_email,
        "timeout_seconds": overrides.timeout_seconds,
        "max_retries": overrides.max_retries,
        "dry_run": overrides.dry_run,
    }
    return {key: value for key, value in values.items() if value is not None}


def _has_complete_direct_overrides(overrides: TaigaConfigOverrides) -> bool:
    return all(
        (
            overrides.base_url,
            overrides.project_identifier,
            overrides.auth_mode,
            overrides.token_environment_key or overrides.token_reference,
        )
    )
