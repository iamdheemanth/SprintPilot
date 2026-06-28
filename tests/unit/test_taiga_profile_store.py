from __future__ import annotations

from pathlib import Path

from sprintpilot.integrations.taiga.profile_store import (
    RepoTaigaBindingStore,
    TaigaConnectionProfile,
    TaigaProfileStore,
)


def test_user_profile_store_persists_non_secret_profile_data(tmp_path: Path) -> None:
    store = TaigaProfileStore(config_dir=tmp_path)
    profile = TaigaConnectionProfile(
        name="acme",
        base_url="https://taiga.example.com/",
        project_identifier="core-platform",
        auth_mode="bearer",
        token_environment_key="SPRINTPILOT_TAIGA_TOKEN",
    )

    store.save_profile(profile, make_default=True)
    loaded = store.get_profile("acme")

    assert loaded is not None
    assert loaded.base_url == "https://taiga.example.com"
    assert loaded.project_identifier == "core-platform"
    assert store.get_default_profile_name() == "acme"
    raw = (tmp_path / "taiga-profiles.json").read_text(encoding="utf-8")
    assert "SPRINTPILOT_TAIGA_TOKEN" in raw
    assert "secret-token" not in raw


def test_user_profile_store_supports_multiple_named_profiles(tmp_path: Path) -> None:
    store = TaigaProfileStore(config_dir=tmp_path)

    store.save_profile(
        TaigaConnectionProfile(
            name="work",
            base_url="https://work.taiga.test",
            project_identifier="work-project",
            auth_mode="application-token",
            token_environment_key="WORK_TAIGA_TOKEN",
        ),
        make_default=True,
    )
    store.save_profile(
        TaigaConnectionProfile(
            name="personal",
            base_url="https://personal.taiga.test",
            project_identifier="personal-project",
            auth_mode="bearer",
            token_environment_key="PERSONAL_TAIGA_TOKEN",
        )
    )

    assert [profile.name for profile in store.list_profiles()] == ["personal", "work"]
    assert store.get_profile("personal").project_identifier == "personal-project"  # type: ignore[union-attr]
    assert store.get_default_profile_name() == "work"


def test_repo_binding_store_persists_only_active_profile_name(tmp_path: Path) -> None:
    store = RepoTaigaBindingStore(repo_dir=tmp_path)

    store.set_active_profile("work")

    assert store.get_active_profile_name() == "work"
    raw = (tmp_path / ".sprintpilot" / "taiga.json").read_text(encoding="utf-8")
    assert "work" in raw
    assert "https://" not in raw
    assert "TOKEN" not in raw
    assert "secret" not in raw.lower()
