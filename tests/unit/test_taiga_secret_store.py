from __future__ import annotations

from sprintpilot.integrations.taiga.secret_store import (
    CompositeTaigaSecretStore,
    EnvironmentTaigaSecretStore,
)


class EmptyStore:
    def get_token(self, reference: str) -> str | None:
        return None


def test_environment_secret_store_resolves_token_without_persisting_it(monkeypatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-token")

    store = EnvironmentTaigaSecretStore()

    assert store.get_token("SPRINTPILOT_TAIGA_TOKEN") == "secret-token"
    assert "secret-token" not in repr(store)


def test_composite_secret_store_falls_back_to_environment(monkeypatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-token")

    store = CompositeTaigaSecretStore(stores=[EmptyStore(), EnvironmentTaigaSecretStore()])

    assert store.get_token("SPRINTPILOT_TAIGA_TOKEN") == "secret-token"
