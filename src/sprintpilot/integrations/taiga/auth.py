"""Taiga authentication helpers."""

from __future__ import annotations

import os

from sprintpilot.integrations.taiga.models import TaigaAuth, TaigaAuthMode, TaigaSettings
from sprintpilot.integrations.taiga.secret_store import CompositeTaigaSecretStore, TaigaSecretStore


def resolve_taiga_auth(
    settings: TaigaSettings,
    *,
    secret_store: TaigaSecretStore | None = None,
) -> TaigaAuth:
    """Resolve Taiga auth headers from configured environment keys."""

    token = _resolve_token(settings, secret_store=secret_store)
    if not token:
        if settings.token_environment_key:
            raise ValueError(
                f"Taiga token environment variable {settings.token_environment_key} is required"
            )
        raise ValueError(f"Taiga token reference {settings.token_reference} is required")

    if settings.auth_mode is TaigaAuthMode.BEARER:
        header_value = f"Bearer {token}"
    elif settings.auth_mode is TaigaAuthMode.APPLICATION_TOKEN:
        header_value = f"Application {token}"
    else:
        raise ValueError(f"Unsupported Taiga authentication mode: {settings.auth_mode}")

    return TaigaAuth(
        mode=settings.auth_mode,
        identity=settings.username_or_email,
        headers={"Authorization": header_value},
    )


def _resolve_token(
    settings: TaigaSettings,
    *,
    secret_store: TaigaSecretStore | None,
) -> str:
    if settings.token_environment_key:
        return os.getenv(settings.token_environment_key, "").strip()
    if settings.token_reference:
        store = secret_store or CompositeTaigaSecretStore()
        return store.get_token(settings.token_reference) or ""
    return ""
