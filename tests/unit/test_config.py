from __future__ import annotations

import os

import pytest

from sprintpilot.config import RuntimeSettings


def test_runtime_settings_load_provider_config_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "stub")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "stub-model")
    monkeypatch.setenv("SPRINTPILOT_PROVIDER_ENV_KEYS", "SPRINTPILOT_STUB_API_KEY,SPRINTPILOT_OTHER_KEY")

    settings = RuntimeSettings.from_env()

    assert settings.llm.provider_name == "stub"
    assert settings.llm.model_name == "stub-model"
    assert settings.llm.environment_keys == ["SPRINTPILOT_STUB_API_KEY", "SPRINTPILOT_OTHER_KEY"]


def test_runtime_settings_loads_project_dotenv_without_overriding_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SPRINTPILOT_MODEL_PROVIDER", raising=False)
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "env-model")
    monkeypatch.delenv("SPRINTPILOT_PROVIDER_ENV_KEYS", raising=False)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "SPRINTPILOT_MODEL_PROVIDER=openrouter",
                "SPRINTPILOT_MODEL_NAME=dotenv-model",
                "SPRINTPILOT_PROVIDER_ENV_KEYS=OPENROUTER_API_KEY",
                "OPENROUTER_API_KEY=sk-secret-value",
            ]
        ),
        encoding="utf-8",
    )

    settings = RuntimeSettings.from_env()

    assert settings.llm.provider_name == "openrouter"
    assert settings.llm.model_name == "env-model"
    assert settings.llm.environment_keys == ["OPENROUTER_API_KEY"]


def test_runtime_settings_exposes_dotenv_values_to_provider_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SPRINTPILOT_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("SPRINTPILOT_MODEL_NAME", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "SPRINTPILOT_MODEL_PROVIDER=openrouter",
                "SPRINTPILOT_MODEL_NAME=meta-llama/llama-3.3-70b-instruct:free",
                "OPENROUTER_API_KEY=test-openrouter-key",
            ]
        ),
        encoding="utf-8",
    )

    settings = RuntimeSettings.from_env()

    assert settings.llm.model_name == "meta-llama/llama-3.3-70b-instruct:free"
    assert os.getenv("OPENROUTER_API_KEY") == "test-openrouter-key"
    os.environ.pop("OPENROUTER_API_KEY", None)


def test_runtime_settings_default_to_openrouter_free_provider(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SPRINTPILOT_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("SPRINTPILOT_MODEL_NAME", raising=False)
    monkeypatch.delenv("SPRINTPILOT_PROVIDER_ENV_KEYS", raising=False)

    settings = RuntimeSettings.from_env()

    assert settings.llm.provider_name == "openrouter"
    assert settings.llm.model_name == "openai/gpt-oss-20b:free"
    assert settings.llm.fallback_models == [
        "nvidia/nemotron-nano-9b-v2:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "google/gemma-4-31b-it:free",
    ]
    assert settings.llm.max_retries == 2
    assert settings.llm.timeout_seconds == 120
    assert settings.llm.environment_keys == ["OPENROUTER_API_KEY", "SPRINTPILOT_OPENROUTER_API_KEY"]


def test_runtime_settings_loads_fallback_models_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "openrouter")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "openai/gpt-oss-20b:free")
    monkeypatch.setenv(
        "SPRINTPILOT_FALLBACK_MODELS",
        "meta-llama/llama-3.3-70b-instruct:free, nousresearch/hermes-3-llama-3.1-405b:free",
    )

    settings = RuntimeSettings.from_env()

    assert settings.llm.fallback_models == [
        "meta-llama/llama-3.3-70b-instruct:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
    ]


def test_runtime_settings_loads_retry_count_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "openrouter")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "openrouter/free")
    monkeypatch.setenv("SPRINTPILOT_MODEL_MAX_RETRIES", "4")

    settings = RuntimeSettings.from_env()

    assert settings.llm.max_retries == 4


def test_runtime_settings_loads_timeout_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "openrouter")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "openai/gpt-oss-20b:free")
    monkeypatch.setenv("SPRINTPILOT_MODEL_TIMEOUT_SECONDS", "45")

    settings = RuntimeSettings.from_env()

    assert settings.llm.timeout_seconds == 45


def test_runtime_settings_configures_gemini_api_key_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "gemini-2.5-flash")
    monkeypatch.delenv("SPRINTPILOT_PROVIDER_ENV_KEYS", raising=False)
    monkeypatch.delenv("SPRINTPILOT_FALLBACK_MODELS", raising=False)
    monkeypatch.delenv("SPRINTPILOT_MODEL_MAX_RETRIES", raising=False)
    monkeypatch.delenv("SPRINTPILOT_MODEL_TIMEOUT_SECONDS", raising=False)

    settings = RuntimeSettings.from_env()

    assert settings.llm.provider_name == "gemini"
    assert settings.llm.model_name == "gemini-2.5-flash"
    assert settings.llm.environment_keys == ["GEMINI_API_KEY", "SPRINTPILOT_GEMINI_API_KEY"]
    assert settings.llm.fallback_models == []
    assert settings.llm.max_retries == 0
    assert settings.llm.timeout_seconds is None


def test_runtime_settings_uses_default_provider_when_only_model_is_set(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SPRINTPILOT_MODEL_PROVIDER", raising=False)
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "stub-model")

    settings = RuntimeSettings.from_env()

    assert settings.llm.provider_name == "openrouter"
    assert settings.llm.model_name == "stub-model"


def test_runtime_settings_error_does_not_echo_secret_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "stub")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", "stub-model")
    monkeypatch.setenv("SPRINTPILOT_PROVIDER_ENV_KEYS", "sk-secret-value")

    with pytest.raises(ValueError) as exc_info:
        RuntimeSettings.from_env()

    assert "sk-secret-value" not in str(exc_info.value)


def test_runtime_settings_missing_model_error_names_checked_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPRINTPILOT_MODEL_PROVIDER", "openrouter")
    monkeypatch.setenv("SPRINTPILOT_MODEL_NAME", " ")

    with pytest.raises(ValueError) as exc_info:
        RuntimeSettings.from_env()

    message = str(exc_info.value)
    assert "SPRINTPILOT_MODEL_NAME" in message
    assert ".env" in message
