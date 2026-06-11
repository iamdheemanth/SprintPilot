"""Gemini provider implementation for SprintPilot's LLM boundary."""

from __future__ import annotations

import os
import re
from typing import Any

from pydantic import BaseModel

from sprintpilot.llm.exceptions import LLMExecutionError
from sprintpilot.llm.models import LLMProviderConfig, LLMRequest, LLMResponse
from sprintpilot.llm.provider import LLMProvider

_ALLOWED_USAGE_COUNTERS = {
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cached_tokens",
    "reasoning_tokens",
}


class GeminiProvider(LLMProvider):
    """Adapter for Google's official Gemini Gen AI SDK."""

    def __init__(self, config: LLMProviderConfig) -> None:
        self._config = config

    @property
    def config(self) -> LLMProviderConfig:
        return self._config

    def execute(self, request: LLMRequest) -> LLMResponse:
        api_key = self._resolve_api_key()
        client = self._create_client(api_key)
        contents = _contents_from_messages(request)
        generation_config = self._generation_config(request)

        try:
            response = client.models.generate_content(
                model=request.model or self._config.model_name,
                contents=contents,
                config=generation_config,
            )
        except Exception as exc:
            raise LLMExecutionError(
                f"Gemini request failed: {_safe_exception_message(exc)}",
                provider_name=self._config.provider_name,
            ) from exc

        return _response_from_generation(response, model=request.model or self._config.model_name)

    def _resolve_api_key(self) -> str:
        environment_keys = self._config.environment_keys or [
            "GEMINI_API_KEY",
            "SPRINTPILOT_GEMINI_API_KEY",
        ]
        for key in environment_keys:
            value = os.getenv(key, "").strip()
            if value:
                return value

        joined_names = ", ".join(environment_keys)
        raise LLMExecutionError(
            f"Gemini API key is required in one of: {joined_names}",
            provider_name=self._config.provider_name,
        )

    def _create_client(self, api_key: str) -> Any:
        try:
            from google import genai
        except ImportError as exc:
            raise LLMExecutionError(
                "Gemini provider requires the google-genai package",
                provider_name=self._config.provider_name,
            ) from exc
        return genai.Client(api_key=api_key)

    def _generation_config(self, request: LLMRequest) -> Any:
        try:
            from google.genai import types
        except ImportError as exc:
            raise LLMExecutionError(
                "Gemini provider requires google.genai.types from the google-genai package",
                provider_name=self._config.provider_name,
            ) from exc

        config: dict[str, Any] = {}
        system_instruction = _system_instruction_from_messages(request)
        if system_instruction:
            config["system_instruction"] = system_instruction
        if request.temperature is not None:
            config["temperature"] = request.temperature
        if request.max_tokens is not None:
            config["max_output_tokens"] = request.max_tokens
        if request.response_schema is not None:
            config["response_mime_type"] = "application/json"
            schema = _response_schema_for_gemini(request.response_schema)
            if _is_pydantic_model_schema(schema):
                config["response_schema"] = schema
            else:
                config["response_json_schema"] = schema
        if self._config.timeout_seconds is not None:
            config["http_options"] = {"timeout": _timeout_milliseconds(self._config.timeout_seconds)}
        return types.GenerateContentConfig(**config)


def _contents_from_messages(request: LLMRequest) -> list[dict[str, Any]]:
    contents = [
        {
            "role": _gemini_role(message.role),
            "parts": [{"text": message.content}],
        }
        for message in request.messages
        if message.role != "system"
    ]
    if contents:
        return contents
    return [{"role": "user", "parts": [{"text": _system_instruction_from_messages(request)}]}]


def _system_instruction_from_messages(request: LLMRequest) -> str:
    return "\n\n".join(message.content for message in request.messages if message.role == "system")


def _gemini_role(role: str) -> str:
    if role == "assistant":
        return "model"
    return "user"


def _response_schema_for_gemini(response_schema: dict[str, Any]) -> dict[str, Any]:
    schema = response_schema.get("schema")
    if isinstance(schema, dict) or _is_pydantic_model_schema(schema):
        return schema
    return response_schema


def _is_pydantic_model_schema(value: Any) -> bool:
    return isinstance(value, type) and issubclass(value, BaseModel)


def _response_from_generation(response: Any, *, model: str) -> LLMResponse:
    content = _response_text(response)
    if not isinstance(content, str) or not content.strip():
        finish_reason = _finish_reason(response)
        detail = f" Finish reason: {finish_reason}." if finish_reason else ""
        raise LLMExecutionError(
            f"Gemini response did not include usable text content.{detail}",
            provider_name="gemini",
        )

    return LLMResponse(
        content=content,
        model=_optional_str(getattr(response, "model_version", None)) or model,
        finish_reason=_finish_reason(response),
        usage=_usage_from_metadata(getattr(response, "usage_metadata", None)),
        raw_metadata=_raw_metadata_from_response(response),
    )


def _response_text(response: Any) -> str | None:
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text

    candidates = getattr(response, "candidates", None)
    if not isinstance(candidates, list) or not candidates:
        return None
    first_candidate = candidates[0]
    content = getattr(first_candidate, "content", None)
    parts = getattr(content, "parts", None)
    if not isinstance(parts, list):
        return None
    texts = [
        part_text
        for part in parts
        if isinstance((part_text := getattr(part, "text", None)), str)
    ]
    return "".join(texts) if texts else None


def _finish_reason(response: Any) -> str | None:
    candidates = getattr(response, "candidates", None)
    if not isinstance(candidates, list) or not candidates:
        return None
    reason = getattr(candidates[0], "finish_reason", None)
    if isinstance(reason, str):
        return reason
    name = getattr(reason, "name", None)
    return name if isinstance(name, str) else None


def _usage_from_metadata(usage_metadata: Any) -> dict[str, int | float]:
    usage = {
        "prompt_tokens": _metadata_number(usage_metadata, "prompt_token_count"),
        "completion_tokens": _metadata_number(usage_metadata, "candidates_token_count"),
        "total_tokens": _metadata_number(usage_metadata, "total_token_count"),
        "cached_tokens": _metadata_number(usage_metadata, "cached_content_token_count"),
        "reasoning_tokens": _metadata_number(usage_metadata, "thoughts_token_count"),
    }
    return {
        key: value
        for key, value in usage.items()
        if key in _ALLOWED_USAGE_COUNTERS and value is not None
    }


def _raw_metadata_from_response(response: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    response_id = _optional_str(getattr(response, "response_id", None))
    if response_id is None:
        response_id = _optional_str(getattr(response, "id", None))
    if response_id is not None:
        metadata["id"] = response_id
    return metadata


def _metadata_number(source: Any, name: str) -> int | float | None:
    value = getattr(source, name, None)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def _timeout_milliseconds(timeout_seconds: float) -> int:
    return max(1, round(timeout_seconds * 1000))


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _safe_exception_message(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return _redact_secret_values(message)


def _redact_secret_values(value: str) -> str:
    redacted = re.sub(r"AIza[A-Za-z0-9._~+/=-]+", "AIza[filtered]", value)
    redacted = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [filtered]", redacted)
    redacted = re.sub(r"sk-[A-Za-z0-9._~+/=-]+", "sk-[filtered]", redacted)
    return re.sub(r"secret-[A-Za-z0-9._~+/=-]+", "secret-[filtered]", redacted)
