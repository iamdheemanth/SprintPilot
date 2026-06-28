from __future__ import annotations

from pathlib import Path

from tests.unit.test_core_v1_mocked_pipeline import InternshipTrackerProvider
from tests.unit.fixtures.test_taiga_sprint_plan import make_taiga_sprint_plan

from sprintpilot.cli import (
    PLAN_EXIT_CONFIG,
    PLAN_EXIT_INPUT,
    PLAN_EXIT_OK,
    _console_safe_message,
    run_diagnostics_command,
    run_plan_command,
    run_taiga_export_command,
)
from sprintpilot.domain import SprintPlan
from sprintpilot.integrations.taiga.client import MatchResult, TaigaClientProtocol
from sprintpilot.integrations.taiga.models import TaigaItemRef
from sprintpilot.integrations.taiga.profile_store import RepoTaigaBindingStore, TaigaConnectionProfile, TaigaProfileStore
from sprintpilot.llm import (
    LLMExecutionError,
    LLMProvider,
    LLMProviderConfig,
    LLMProviderHealthCheckResult,
    LLMRequest,
    LLMResponse,
)


class FailingProvider(LLMProvider):
    @property
    def config(self) -> LLMProviderConfig:
        return LLMProviderConfig(provider_name="openrouter", model_name="openrouter/free")

    def execute(self, request: LLMRequest) -> LLMResponse:
        raise LLMExecutionError(
            "OpenRouter did not return a usable chat completion because the response was missing choices",
            provider_name="openrouter",
        )


class HealthyDiagnosticsProvider(LLMProvider):
    @property
    def config(self) -> LLMProviderConfig:
        return LLMProviderConfig(
            provider_name="openrouter",
            model_name="openai/gpt-oss-20b:free",
            fallback_models=[
                "meta-llama/llama-3.3-70b-instruct:free",
                "nousresearch/hermes-3-llama-3.1-405b:free",
            ],
            max_retries=2,
            environment_keys=["OPENROUTER_API_KEY"],
        )

    def execute(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content='{"status":"ok"}')

    def check_health(self) -> LLMProviderHealthCheckResult:
        return LLMProviderHealthCheckResult(
            request_sent=True,
            response_received=True,
            structured_output_supported=True,
            elapsed_ms=42,
            http_status=200,
            response_id="gen-health",
        )


class HealthyGeminiDiagnosticsProvider(LLMProvider):
    @property
    def config(self) -> LLMProviderConfig:
        return LLMProviderConfig(
            provider_name="gemini",
            model_name="gemini-2.5-flash",
            environment_keys=["GEMINI_API_KEY"],
        )

    def execute(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content='{"status":"ok"}',
            model=self.config.model_name,
            raw_metadata={"id": "gemini-health"},
        )


class FailingDiagnosticsProvider(HealthyDiagnosticsProvider):
    def check_health(self) -> LLMProviderHealthCheckResult:
        return LLMProviderHealthCheckResult(
            request_sent=True,
            response_received=False,
            structured_output_supported=False,
            elapsed_ms=5001,
            error_message="OpenRouter request failed before receiving a response",
            provider_error="Response timed out",
        )


class RecordingCliTaigaClient(TaigaClientProtocol):
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.next_id = 100

    def resolve_project(self, settings, auth):
        self.calls.append(f"resolve_project:{settings.project_identifier}")
        from sprintpilot.integrations.taiga.models import TaigaProjectRef

        return TaigaProjectRef(identifier=settings.project_identifier, project_id=42)

    def find_existing_epic(self, project, source_ref, title=None):
        self.calls.append(f"find_epic:{source_ref.source_id}")
        return MatchResult.no_match()

    def find_existing_user_story(self, project, source_ref, title=None):
        self.calls.append(f"find_story:{source_ref.source_id}")
        return MatchResult.no_match()

    def find_existing_task(self, project, user_story_ref, source_ref, subject=None):
        self.calls.append(f"find_task:{source_ref.source_id}")
        return MatchResult.no_match()

    def create_epic(self, payload):
        self.calls.append(f"create_epic:{payload.source_ref.source_id}")
        self.next_id += 1
        return TaigaItemRef(item_type="epic", item_id=self.next_id, subject=payload.subject)

    def create_user_story(self, payload):
        self.calls.append(f"create_story:{payload.source_ref.source_id}")
        self.next_id += 1
        return TaigaItemRef(item_type="user_story", item_id=self.next_id, subject=payload.subject)

    def create_task(self, payload):
        self.calls.append(f"create_task:{payload.source_ref.source_id}")
        self.next_id += 1
        return TaigaItemRef(item_type="task", item_id=self.next_id, subject=payload.subject)


def _write_sprint_plan_json(tmp_path: Path) -> Path:
    path = tmp_path / "sprint-plan.json"
    path.write_text(make_taiga_sprint_plan().model_dump_json(), encoding="utf-8")
    return path


def _configure_taiga(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPRINTPILOT_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "stub")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "stub-model")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_BASE_URL", "https://taiga.example.com")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_PROJECT", "project-slug")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_AUTH_MODE", "bearer")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN_ENV_KEY", "SPRINTPILOT_TAIGA_TOKEN")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-taiga-token")


def test_plan_command_requires_exactly_one_idea_source(tmp_path: Path) -> None:
    missing = run_plan_command(output=tmp_path, provider=InternshipTrackerProvider())
    both = run_plan_command(
        idea="Build a student internship tracking platform.",
        idea_file=tmp_path / "idea.txt",
        output=tmp_path,
        provider=InternshipTrackerProvider(),
    )

    assert missing.exit_code == PLAN_EXIT_INPUT
    assert both.exit_code == PLAN_EXIT_INPUT


def test_plan_command_dry_run_validates_inputs_without_generation(tmp_path: Path) -> None:
    result = run_plan_command(
        idea="Build a student internship tracking platform.",
        output=tmp_path,
        dry_run=True,
    )

    assert result.exit_code == 0
    assert result.report_path is None
    assert "validated" in result.message.lower()


def test_plan_command_returns_validation_error_when_provider_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SPRINTPILOT_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("SPRINTPILOT_MODEL_NAME", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("SPRINTPILOT_OPENROUTER_API_KEY", raising=False)
    result = run_plan_command(
        idea="Build a student internship tracking platform.",
        output=tmp_path,
    )

    assert result.exit_code == PLAN_EXIT_CONFIG
    assert "provider" in result.message.lower()


def test_plan_command_reports_runtime_provider_errors_without_workflow_validation_prefix(
    tmp_path: Path,
) -> None:
    result = run_plan_command(
        idea="Build a student internship tracking platform.",
        output=tmp_path,
        provider=FailingProvider(),
    )

    assert result.exit_code == PLAN_EXIT_CONFIG
    assert result.message.startswith("LLM provider error:")
    assert "missing choices" in result.message
    assert "workflow validation" not in result.message.lower()
    assert "unsupported model provider configuration" not in result.message.lower()


def test_plan_command_reports_resolved_provider_and_model_before_workflow(
    tmp_path: Path,
) -> None:
    startup_messages: list[str] = []

    result = run_plan_command(
        idea="Build a student internship tracking platform.",
        output=tmp_path,
        provider=InternshipTrackerProvider(),
        on_start=startup_messages.append,
    )

    assert result.exit_code == 0
    assert startup_messages == ["Provider: mock\nModel: mock-core-v1\nFallbacks: 0\nRetries: 0"]


def test_plan_command_startup_message_reports_fallback_count_and_retries(
    tmp_path: Path,
) -> None:
    startup_messages: list[str] = []

    result = run_plan_command(
        idea="Build a student internship tracking platform.",
        output=tmp_path,
        provider=HealthyDiagnosticsProvider(),
        on_start=startup_messages.append,
    )

    assert result.exit_code != 0
    assert startup_messages == [
        "Provider: openrouter\n"
        "Model: openai/gpt-oss-20b:free\n"
        "Fallbacks: 2\n"
        "Retries: 2"
    ]


def test_plan_command_startup_message_does_not_leak_secret_values(tmp_path: Path) -> None:
    startup_messages: list[str] = []

    result = run_plan_command(
        idea="Build a student internship tracking platform.",
        output=tmp_path,
        provider=InternshipTrackerProvider(),
        on_start=startup_messages.append,
    )

    assert result.exit_code == 0
    assert "OPENROUTER_API_KEY" not in startup_messages[0]
    assert "sk-" not in startup_messages[0]


def test_full_mocked_core_v1_workflow_writes_markdown_report(tmp_path: Path) -> None:
    result = run_plan_command(
        idea="Build a student internship tracking platform.",
        output=tmp_path,
        title="Student Internship Tracker",
        provider=InternshipTrackerProvider(),
    )

    assert result.exit_code == 0
    assert result.report_path is not None
    assert result.report_path.exists()
    markdown = result.report_path.read_text(encoding="utf-8")
    assert "# SprintPilot Report: Student Internship Tracker" in markdown
    assert "Engineering Confidence Assessment" in markdown


def test_plan_command_writes_structured_sprint_plan_artifact(tmp_path: Path) -> None:
    result = run_plan_command(
        idea="Build a student internship tracking platform.",
        output=tmp_path,
        title="Student Internship Tracker",
        provider=InternshipTrackerProvider(),
    )

    assert result.exit_code == 0
    assert result.report_path is not None
    sprint_plan_path = result.report_path.with_name(f"{result.report_path.stem}.sprint-plan.json")
    assert sprint_plan_path.exists()

    sprint_plan = SprintPlan.model_validate_json(sprint_plan_path.read_text(encoding="utf-8"))
    assert sprint_plan.epics[0].id == "EPIC-001"
    assert sprint_plan.stories[0].id == "SP-001"
    assert sprint_plan.tasks[0].story_id == "SP-001"


def test_taiga_export_command_accepts_sprint_plan_artifact_from_normal_plan_run(
    monkeypatch,
    tmp_path: Path,
) -> None:
    plan_result = run_plan_command(
        idea="Build a student internship tracking platform.",
        output=tmp_path,
        title="Student Internship Tracker",
        provider=InternshipTrackerProvider(),
    )
    assert plan_result.report_path is not None
    sprint_plan_path = plan_result.report_path.with_name(
        f"{plan_result.report_path.stem}.sprint-plan.json"
    )
    _configure_taiga(monkeypatch, tmp_path)
    client = RecordingCliTaigaClient()

    export_result = run_taiga_export_command(
        sprint_plan_file=sprint_plan_path,
        dry_run=True,
        client_factory=lambda: client,
    )

    assert export_result.exit_code == PLAN_EXIT_OK
    assert export_result.sync_result is not None
    assert export_result.sync_result.dry_run is True
    assert "Mode: dry-run" in export_result.message
    assert len(export_result.sync_result.previewed) == 4
    assert client.calls == []


def test_diagnostics_command_reports_provider_configuration_without_secrets(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-secret-value")

    result = run_diagnostics_command(provider=HealthyDiagnosticsProvider())

    assert result.exit_code == 0
    assert "Provider: openrouter" in result.message
    assert "Model: openai/gpt-oss-20b:free" in result.message
    assert "Fallbacks: 2" in result.message
    assert "Retries: 2" in result.message
    assert "API Key: Present" in result.message
    assert "✓ Request sent" in result.message
    assert "✓ Response received" in result.message
    assert "✓ Structured output supported" in result.message
    assert "sk-secret-value" not in result.message
    assert "OPENROUTER_API_KEY" not in result.message


def test_diagnostics_command_reports_gemini_base_health_check_success(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "secret-gemini-key")

    result = run_diagnostics_command(provider=HealthyGeminiDiagnosticsProvider(), verbose=True)

    assert result.exit_code == 0
    assert "Provider: gemini" in result.message
    assert "Model: gemini-2.5-flash" in result.message
    assert "API Key: Present" in result.message
    assert "✓ Request sent" in result.message
    assert "✓ Response received" in result.message
    assert "✓ Structured output supported" in result.message
    assert "Response ID: gemini-health" in result.message
    assert "secret-gemini-key" not in result.message


def test_diagnostics_command_verbose_reports_sanitized_provider_metadata(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-secret-value")

    result = run_diagnostics_command(provider=HealthyDiagnosticsProvider(), verbose=True)

    assert result.exit_code == 0
    assert "HTTP Status: 200" in result.message
    assert "Response ID: gen-health" in result.message
    assert "Elapsed: 42 ms" in result.message
    assert "sk-secret-value" not in result.message


def test_diagnostics_command_reports_health_check_failure(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-secret-value")

    result = run_diagnostics_command(provider=FailingDiagnosticsProvider(), verbose=True)

    assert result.exit_code == PLAN_EXIT_CONFIG
    assert "✗ Response received" in result.message
    assert "Provider Error: Response timed out" in result.message
    assert "Elapsed: 5001 ms" in result.message


def test_console_safe_message_replaces_status_symbols_for_legacy_windows_encoding() -> None:
    message = "✓ Request sent\n✗ Response received"

    assert _console_safe_message(message, encoding="cp1252") == (
        "OK Request sent\nFAIL Response received"
    )
    assert _console_safe_message(message, encoding="utf-8") == message


def test_taiga_export_command_dry_run_previews_backlog_items_without_mutation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _configure_taiga(monkeypatch, tmp_path)
    client = RecordingCliTaigaClient()

    result = run_taiga_export_command(
        sprint_plan_file=_write_sprint_plan_json(tmp_path),
        dry_run=True,
        client_factory=lambda: client,
    )

    assert result.exit_code == PLAN_EXIT_OK
    assert result.sync_result is not None
    assert result.sync_result.dry_run is True
    assert len(result.sync_result.previewed) == 4
    assert client.calls == []
    assert "Provider: stub" in result.message
    assert "Model: stub-model" in result.message
    assert "Taiga project: project-slug" in result.message
    assert "Mode: dry-run" in result.message
    assert "Previewed: 4" in result.message
    assert "secret-taiga-token" not in result.message
    assert "sprint assignment" not in result.message.lower()


def test_taiga_export_command_live_mode_uses_mocked_client(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _configure_taiga(monkeypatch, tmp_path)
    client = RecordingCliTaigaClient()

    result = run_taiga_export_command(
        sprint_plan_file=_write_sprint_plan_json(tmp_path),
        live=True,
        client_factory=lambda: client,
    )

    assert result.exit_code == PLAN_EXIT_OK
    assert result.sync_result is not None
    assert result.sync_result.dry_run is False
    assert [item.item_type for item in result.sync_result.created] == [
        "epic",
        "user_story",
        "task",
        "task",
    ]
    assert "resolve_project:project-slug" in client.calls
    assert "Created: 4" in result.message
    assert "Mode: live" in result.message


def test_taiga_export_command_uses_repo_bound_profile_without_legacy_env(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPRINTPILOT_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "stub")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "stub-model")
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-taiga-token")
    for key in (
        "SPRINTPILOT_TAIGA_BASE_URL",
        "SPRINTPILOT_TAIGA_PROJECT",
        "SPRINTPILOT_TAIGA_AUTH_MODE",
        "SPRINTPILOT_TAIGA_TOKEN_ENV_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    TaigaProfileStore(config_dir=tmp_path / "config").save_profile(
        TaigaConnectionProfile(
            name="repo-profile",
            base_url="https://profile.taiga.test",
            project_identifier="profile-project",
            auth_mode="bearer",
            token_environment_key="SPRINTPILOT_TAIGA_TOKEN",
        )
    )
    RepoTaigaBindingStore(repo_dir=tmp_path).set_active_profile("repo-profile")
    client = RecordingCliTaigaClient()

    result = run_taiga_export_command(
        sprint_plan_file=_write_sprint_plan_json(tmp_path),
        dry_run=True,
        client_factory=lambda: client,
    )

    assert result.exit_code == PLAN_EXIT_OK
    assert "Taiga project: profile-project" in result.message
    assert "secret-taiga-token" not in result.message
    assert client.calls == []


def test_taiga_export_command_explicit_overrides_take_precedence_over_repo_profile(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPRINTPILOT_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "stub")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "stub-model")
    monkeypatch.setenv("OVERRIDE_TAIGA_TOKEN", "secret-taiga-token")
    TaigaProfileStore(config_dir=tmp_path / "config").save_profile(
        TaigaConnectionProfile(
            name="repo-profile",
            base_url="https://profile.taiga.test",
            project_identifier="profile-project",
            auth_mode="bearer",
            token_environment_key="PROFILE_TAIGA_TOKEN",
        )
    )
    RepoTaigaBindingStore(repo_dir=tmp_path).set_active_profile("repo-profile")
    client = RecordingCliTaigaClient()

    result = run_taiga_export_command(
        sprint_plan_file=_write_sprint_plan_json(tmp_path),
        dry_run=True,
        taiga_base_url="https://override.taiga.test",
        taiga_project="override-project",
        taiga_auth_mode="bearer",
        taiga_token_env_key="OVERRIDE_TAIGA_TOKEN",
        client_factory=lambda: client,
    )

    assert result.exit_code == PLAN_EXIT_OK
    assert "Taiga project: override-project" in result.message
    assert "profile-project" not in result.message


def test_taiga_export_command_reports_missing_config_before_sync(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPRINTPILOT_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "stub")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "stub-model")
    for key in (
        "SPRINTPILOT_TAIGA_BASE_URL",
        "SPRINTPILOT_TAIGA_PROJECT",
        "SPRINTPILOT_TAIGA_AUTH_MODE",
        "SPRINTPILOT_TAIGA_TOKEN_ENV_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    client = RecordingCliTaigaClient()

    result = run_taiga_export_command(
        sprint_plan_file=_write_sprint_plan_json(tmp_path),
        live=True,
        client_factory=lambda: client,
    )

    assert result.exit_code == PLAN_EXIT_CONFIG
    assert "Missing Taiga configuration" in result.message
    assert client.calls == []


def test_taiga_export_command_preserves_legacy_dotenv_fallback(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPRINTPILOT_CONFIG_HOME", str(tmp_path / "config"))
    for key in (
        "SPRINTPILOT_MODEL_PROVIDER",
        "SPRINTPILOT_MODEL_NAME",
        "SPRINTPILOT_TAIGA_BASE_URL",
        "SPRINTPILOT_TAIGA_PROJECT",
        "SPRINTPILOT_TAIGA_AUTH_MODE",
        "SPRINTPILOT_TAIGA_TOKEN_ENV_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SPRINTPILOT_TAIGA_TOKEN", "secret-taiga-token")
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "SPRINTPILOT_MODEL_PROVIDER=stub",
                "SPRINTPILOT_MODEL_NAME=stub-model",
                "SPRINTPILOT_TAIGA_BASE_URL=https://legacy-dotenv.taiga.test",
                "SPRINTPILOT_TAIGA_PROJECT=legacy-dotenv-project",
                "SPRINTPILOT_TAIGA_AUTH_MODE=bearer",
                "SPRINTPILOT_TAIGA_TOKEN_ENV_KEY=SPRINTPILOT_TAIGA_TOKEN",
            ]
        ),
        encoding="utf-8",
    )
    client = RecordingCliTaigaClient()

    result = run_taiga_export_command(
        sprint_plan_file=_write_sprint_plan_json(tmp_path),
        dry_run=True,
        client_factory=lambda: client,
    )

    assert result.exit_code == PLAN_EXIT_OK
    assert "Taiga project: legacy-dotenv-project" in result.message
    assert "secret-taiga-token" not in result.message


def test_taiga_export_command_requires_one_mode(tmp_path: Path) -> None:
    result = run_taiga_export_command(
        sprint_plan_file=_write_sprint_plan_json(tmp_path),
        dry_run=True,
        live=True,
    )

    assert result.exit_code == PLAN_EXIT_INPUT
    assert "Choose either dry-run or live" in result.message
