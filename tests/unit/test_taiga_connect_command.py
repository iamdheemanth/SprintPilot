from __future__ import annotations

from pathlib import Path

from sprintpilot.cli import PLAN_EXIT_INPUT, PLAN_EXIT_OK, run_taiga_connect_command
from sprintpilot.integrations.taiga.profile_store import RepoTaigaBindingStore, TaigaProfileStore


def test_taiga_connect_creates_profile_and_binds_current_repo(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    repo_dir = tmp_path / "repo"

    result = run_taiga_connect_command(
        profile_name="acme",
        base_url="https://taiga.example.com/",
        project_identifier="core-platform",
        auth_mode="bearer",
        token_environment_key="SPRINTPILOT_TAIGA_TOKEN",
        make_default=True,
        bind_repo=True,
        config_dir=config_dir,
        repo_dir=repo_dir,
    )

    profile_store = TaigaProfileStore(config_dir=config_dir)
    binding_store = RepoTaigaBindingStore(repo_dir=repo_dir)
    assert result.exit_code == PLAN_EXIT_OK
    assert profile_store.get_profile("acme") is not None
    assert profile_store.get_default_profile_name() == "acme"
    assert binding_store.get_active_profile_name() == "acme"
    assert "Taiga profile 'acme' saved" in result.message
    assert "secret" not in result.message.lower()


def test_taiga_connect_can_bind_existing_profile_without_rewriting_it(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    repo_dir = tmp_path / "repo"
    first = run_taiga_connect_command(
        profile_name="acme",
        base_url="https://taiga.example.com",
        project_identifier="core-platform",
        auth_mode="bearer",
        token_environment_key="SPRINTPILOT_TAIGA_TOKEN",
        bind_repo=False,
        config_dir=config_dir,
        repo_dir=repo_dir,
    )
    second = run_taiga_connect_command(
        profile_name="acme",
        bind_repo=True,
        config_dir=config_dir,
        repo_dir=repo_dir,
    )

    assert first.exit_code == PLAN_EXIT_OK
    assert second.exit_code == PLAN_EXIT_OK
    assert RepoTaigaBindingStore(repo_dir=repo_dir).get_active_profile_name() == "acme"


def test_taiga_connect_requires_profile_details_when_profile_is_new(tmp_path: Path) -> None:
    result = run_taiga_connect_command(
        profile_name="missing-details",
        bind_repo=True,
        config_dir=tmp_path / "config",
        repo_dir=tmp_path / "repo",
    )

    assert result.exit_code == PLAN_EXIT_INPUT
    assert "base URL" in result.message
    assert not (tmp_path / "repo" / ".sprintpilot" / "taiga.json").exists()
