"""Secret lookup helpers for Taiga tokens."""

from __future__ import annotations

import os
from typing import Protocol


class TaigaSecretStore(Protocol):
    """Protocol for resolving a token by non-secret reference."""

    def get_token(self, reference: str) -> str | None:
        ...


class EnvironmentTaigaSecretStore:
    """Fallback secret store that treats references as environment variable names."""

    def get_token(self, reference: str) -> str | None:
        value = os.getenv(reference, "").strip()
        return value or None


class KeyringTaigaSecretStore:
    """Optional OS keyring-backed secret store when the keyring package is installed."""

    def __init__(self, *, service_name: str = "sprintpilot.taiga") -> None:
        self.service_name = service_name

    def get_token(self, reference: str) -> str | None:
        try:
            import keyring  # type: ignore[import-not-found]
        except ModuleNotFoundError:
            return None
        value = keyring.get_password(self.service_name, reference)
        return value.strip() if isinstance(value, str) and value.strip() else None


class CompositeTaigaSecretStore:
    """Tries keyring first, then environment-variable references."""

    def __init__(self, stores: list[TaigaSecretStore] | None = None) -> None:
        self.stores = stores or [KeyringTaigaSecretStore(), EnvironmentTaigaSecretStore()]

    def get_token(self, reference: str) -> str | None:
        for store in self.stores:
            token = store.get_token(reference)
            if token:
                return token
        return None
