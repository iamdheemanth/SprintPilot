from __future__ import annotations

from pathlib import Path

from tests.unit.test_core_v1_mocked_pipeline import InternshipTrackerProvider

from sprintpilot.cli import (
    PLAN_EXIT_CONFIG,
    PLAN_EXIT_INPUT,
    _console_safe_message,
    run_diagnostics_command,
    run_plan_command,
)
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
