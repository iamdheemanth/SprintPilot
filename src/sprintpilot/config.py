"""Runtime configuration for SprintPilot Core v1."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from sprintpilot.llm import LLMProviderConfig

_OPENROUTER_DEFAULT_MODEL = "openai/gpt-oss-20b:free"
_OPENROUTER_DEFAULT_FALLBACK_MODELS = (
    "nvidia/nemotron-nano-9b-v2:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-4-31b-it:free",
)


class RuntimeSettings(BaseModel):
    """Runtime settings used by the Core v1 workflow."""

    model_config = ConfigDict(extra="forbid")

    llm: LLMProviderConfig

    @classmethod
    def from_env(cls) -> "RuntimeSettings":
        dotenv_values = _load_project_dotenv()
        _apply_dotenv_to_environment(dotenv_values)
        provider_name = _runtime_value(
            "SPRINTPILOT_MODEL_PROVIDER",
            dotenv_values,
            default="openrouter",
        ).strip()
        model_name = _runtime_value(
            "SPRINTPILOT_MODEL_NAME",
            dotenv_values,
            default=_OPENROUTER_DEFAULT_MODEL if provider_name.lower() == "openrouter" else "",
        ).strip()
        fallback_models_value = _runtime_value(
            "SPRINTPILOT_FALLBACK_MODELS",
            dotenv_values,
            default=(
                ",".join(_OPENROUTER_DEFAULT_FALLBACK_MODELS)
                if provider_name.lower() == "openrouter"
                else ""
            ),
        )
        provider_env_keys_value = _runtime_value(
            "SPRINTPILOT_PROVIDER_ENV_KEYS",
            dotenv_values,
            default="",
        )
        max_retries_value = _runtime_value(
            "SPRINTPILOT_MODEL_MAX_RETRIES",
            dotenv_values,
            default="2" if provider_name.lower() == "openrouter" else "0",
        ).strip()
        timeout_seconds_value = _runtime_value(
            "SPRINTPILOT_MODEL_TIMEOUT_SECONDS",
            dotenv_values,
            default="120" if provider_name.lower() == "openrouter" else "",
        ).strip()
        environment_keys = [
            key.strip()
            for key in provider_env_keys_value.split(",")
            if key.strip()
        ]
        if not environment_keys and provider_name.lower() == "openrouter":
            environment_keys = ["OPENROUTER_API_KEY", "SPRINTPILOT_OPENROUTER_API_KEY"]
        if not environment_keys and provider_name.lower() == "gemini":
            environment_keys = ["GEMINI_API_KEY", "SPRINTPILOT_GEMINI_API_KEY"]

        if not provider_name:
            raise ValueError(
                "SPRINTPILOT_MODEL_PROVIDER is required; checked environment variables and project .env"
            )
        if not model_name:
            raise ValueError(
                "SPRINTPILOT_MODEL_NAME is required; checked environment variables and project .env"
            )

        try:
            return cls(
                llm=LLMProviderConfig(
                    provider_name=provider_name,
                    model_name=model_name,
                    fallback_models=_parse_csv_list(fallback_models_value),
                    timeout_seconds=_parse_optional_positive_float(
                        timeout_seconds_value,
                        setting_name="SPRINTPILOT_MODEL_TIMEOUT_SECONDS",
                    ),
                    max_retries=_parse_non_negative_int(
                        max_retries_value,
                        setting_name="SPRINTPILOT_MODEL_MAX_RETRIES",
                    ),
                    environment_keys=environment_keys,
                )
            )
        except ValidationError as exc:
            raise ValueError("Invalid SprintPilot runtime LLM configuration") from exc


def _runtime_value(name: str, dotenv_values: dict[str, str], *, default: str) -> str:
    environment_value = os.getenv(name)
    if environment_value is not None:
        return environment_value
    return dotenv_values.get(name, default)


def _parse_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_non_negative_int(value: str, *, setting_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{setting_name} must be a non-negative integer") from exc
    if parsed < 0:
        raise ValueError(f"{setting_name} must be a non-negative integer")
    return parsed


def _parse_optional_positive_float(value: str, *, setting_name: str) -> float | None:
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{setting_name} must be a positive number") from exc
    if parsed <= 0:
        raise ValueError(f"{setting_name} must be a positive number")
    return parsed


def _load_project_dotenv() -> dict[str, str]:
    dotenv_path = _find_project_dotenv()
    if dotenv_path is None:
        return {}

    values: dict[str, str] = {}
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = _strip_dotenv_value(value.strip())
    return values


def _apply_dotenv_to_environment(dotenv_values: dict[str, str]) -> None:
    for key, value in dotenv_values.items():
        if key in _RUNTIME_ONLY_DOTENV_KEYS:
            continue
        os.environ.setdefault(key, value)


def _find_project_dotenv() -> Path | None:
    current = Path.cwd()
    for directory in (current, *current.parents):
        candidate = directory / ".env"
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _strip_dotenv_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


_RUNTIME_ONLY_DOTENV_KEYS = {
    "SPRINTPILOT_MODEL_PROVIDER",
    "SPRINTPILOT_MODEL_NAME",
    "SPRINTPILOT_FALLBACK_MODELS",
    "SPRINTPILOT_PROVIDER_ENV_KEYS",
    "SPRINTPILOT_MODEL_MAX_RETRIES",
    "SPRINTPILOT_MODEL_TIMEOUT_SECONDS",
}
