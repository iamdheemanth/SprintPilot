"""OpenRouter provider implementation for SprintPilot's LLM boundary."""

from __future__ import annotations

import json
import os
import re
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sprintpilot.llm.exceptions import LLMExecutionError
from sprintpilot.llm.models import LLMProviderConfig, LLMRequest, LLMResponse
from sprintpilot.llm.provider import LLMProvider

_ALLOWED_USAGE_COUNTERS = {
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cached_tokens",
}
_TRANSIENT_HTTP_STATUS_CODES = {408, 429, 500, 502, 503, 504}
_BODY_EXCERPT_LIMIT = 500


class OpenRouterProviderError(LLMExecutionError):
    """Raised when OpenRouter returns an unusable provider response."""

    def __init__(
        self,
        message: str,
        *,
        provider_name: str,
        debug_summary: dict[str, Any] | None = None,
    ) -> None:
        self.debug_summary = debug_summary or {}
        super().__init__(message, provider_name=provider_name)


class OpenRouterProvider(LLMProvider):
    """HTTP adapter for OpenRouter's OpenAI-compatible chat completions API."""

    endpoint_url = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, config: LLMProviderConfig) -> None:
        self._config = config

    @property
    def config(self) -> LLMProviderConfig:
        return self._config

    def execute(self, request: LLMRequest) -> LLMResponse:
        api_key = self._resolve_api_key()
        payload = self._request_payload(request)
        http_request = Request(
            self.endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        http_status: int | None = None
        raw_body: str | None = None
        attempts = self._config.max_retries + 1
        for attempt in range(attempts):
            try:
                with urlopen(http_request, timeout=self._config.timeout_seconds) as response:
                    http_status = getattr(response, "status", None)
                    raw_body = response.read().decode("utf-8")
                    break
            except HTTPError as exc:
                if _is_transient_http_error(exc) and attempt < attempts - 1:
                    sleep(_retry_delay_seconds(attempt, exc))
                    continue
                raw_body = _read_http_error_body(exc)
                if raw_body:
                    try:
                        completion = json.loads(raw_body)
                    except json.JSONDecodeError:
                        completion = {}
                    error_message = _extract_error_message(completion)
                    if error_message:
                        raise OpenRouterProviderError(
                            f"OpenRouter request failed with HTTP {exc.code}: {error_message}",
                            provider_name=self._config.provider_name,
                            debug_summary=_debug_summary(
                                completion,
                                http_status=exc.code,
                                raw_body=raw_body,
                            ),
                        ) from exc
                raise LLMExecutionError(
                    f"OpenRouter request failed with HTTP {exc.code}",
                    provider_name=self._config.provider_name,
                ) from exc
            except URLError as exc:
                if attempt < attempts - 1:
                    continue
                raise LLMExecutionError(
                    "OpenRouter request failed before receiving a response",
                    provider_name=self._config.provider_name,
                ) from exc

        if raw_body is None:
            raise LLMExecutionError(
                "OpenRouter request failed before receiving a response",
                provider_name=self._config.provider_name,
            )

        try:
            completion = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise LLMExecutionError(
                "OpenRouter returned invalid JSON",
                provider_name=self._config.provider_name,
            ) from exc

        return self._response_from_completion(completion, http_status=http_status, raw_body=raw_body)

    def _resolve_api_key(self) -> str:
        environment_keys = self._config.environment_keys or [
            "OPENROUTER_API_KEY",
            "SPRINTPILOT_OPENROUTER_API_KEY",
        ]
        for key in environment_keys:
            value = os.getenv(key, "").strip()
            if value:
                return value

        joined_names = ", ".join(environment_keys)
        raise LLMExecutionError(
            f"OpenRouter API key is required in one of: {joined_names}",
            provider_name=self._config.provider_name,
        )

    def _request_payload(self, request: LLMRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model or self._config.model_name,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
        }
        if request.model is None and self._config.fallback_models:
            payload["models"] = list(self._config.fallback_models)
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.response_schema is not None:
            payload["reasoning"] = {"enabled": False, "exclude": True}
            payload["response_format"] = _response_format_from_schema(request.response_schema)
        return payload

    def _response_from_completion(
        self,
        completion: dict[str, Any],
        *,
        http_status: int | None = None,
        raw_body: str | None = None,
    ) -> LLMResponse:
        choices = completion.get("choices")
        if not isinstance(choices, list) or not choices:
            error_message = _extract_error_message(completion)
            detail = f": {error_message}" if error_message else " because the response was missing choices"
            raise OpenRouterProviderError(
                f"OpenRouter did not return a usable chat completion{detail}",
                provider_name=self._config.provider_name,
                debug_summary=_debug_summary(
                    completion,
                    http_status=http_status,
                    raw_body=raw_body,
                ),
            )

        first_choice = choices[0]
        message = first_choice.get("message") if isinstance(first_choice, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise LLMExecutionError(
                "OpenRouter response choice did not include message content",
                provider_name=self._config.provider_name,
            )

        finish_reason = first_choice.get("finish_reason") if isinstance(first_choice, dict) else None
        usage = _sanitize_usage(completion.get("usage"))
        raw_metadata = _sanitize_raw_metadata(completion, http_status=http_status)

        return LLMResponse(
            content=content,
            model=completion.get("model"),
            finish_reason=finish_reason if isinstance(finish_reason, str) else None,
            usage=usage if isinstance(usage, dict) else {},
            raw_metadata=raw_metadata,
        )


def _sanitize_usage(value: Any) -> dict[str, int | float]:
    if not isinstance(value, dict):
        return {}
    return {
        key: counter
        for key, counter in value.items()
        if key in _ALLOWED_USAGE_COUNTERS and _is_number(counter)
    }


def _sanitize_raw_metadata(completion: dict[str, Any], *, http_status: int | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if http_status is not None:
        metadata["http_status"] = http_status
    response_id = completion.get("id")
    if isinstance(response_id, str):
        metadata["id"] = response_id
    return metadata


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_transient_http_error(exc: HTTPError) -> bool:
    return exc.code in _TRANSIENT_HTTP_STATUS_CODES


def _read_http_error_body(exc: HTTPError) -> str | None:
    if exc.fp is None:
        return None
    try:
        body = exc.fp.read()
    except OSError:
        return None
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    if isinstance(body, str):
        return body
    return None


def _extract_error_message(completion: dict[str, Any]) -> str | None:
    error = completion.get("error")
    upstream_detail = _extract_upstream_error_detail(error)
    upstream_detail = _redact_secret_values(upstream_detail) if upstream_detail else None
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            message = message.strip()
            if upstream_detail and upstream_detail not in message:
                return f"{message} ({upstream_detail})"
            return message
    if isinstance(error, str) and error.strip():
        return error.strip()
    if upstream_detail:
        return upstream_detail
    return None


def _extract_upstream_error_detail(error: Any) -> str | None:
    if not isinstance(error, dict):
        return None
    metadata = error.get("metadata")
    if not isinstance(metadata, dict):
        return None
    raw = metadata.get("raw")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _retry_delay_seconds(attempt: int, exc: HTTPError | None = None) -> float:
    retry_after = _retry_after_seconds(exc)
    if retry_after is not None:
        return retry_after
    return min(2**attempt, 4)


def _retry_after_seconds(exc: HTTPError | None) -> float | None:
    if exc is None:
        return None
    headers = getattr(exc, "headers", None)
    if headers is None:
        return None
    try:
        value = headers.get("Retry-After")
    except AttributeError:
        return None
    if value is None:
        return None
    try:
        parsed = float(str(value).strip())
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


def _response_format_from_schema(response_schema: dict[str, Any]) -> dict[str, Any]:
    schema_name = response_schema.get("name")
    if not isinstance(schema_name, str) or not schema_name.strip():
        schema_name = response_schema.get("title")
    if not isinstance(schema_name, str) or not schema_name.strip():
        schema_name = "SprintPilotResponse"

    schema = response_schema.get("schema")
    if not isinstance(schema, dict):
        schema = response_schema

    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name.strip(),
            "strict": True,
            "schema": schema,
        },
    }


def _debug_summary(
    completion: dict[str, Any],
    *,
    http_status: int | None,
    raw_body: str | None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if http_status is not None:
        summary["http_status"] = http_status

    response_id = completion.get("id")
    if isinstance(response_id, str):
        summary["response_id"] = response_id

    error_message = _extract_error_message(completion)
    if error_message is not None:
        summary["error_message"] = _redact_secret_values(error_message)

    body_excerpt = _sanitized_body_excerpt(raw_body)
    if body_excerpt is not None:
        summary["body_excerpt"] = body_excerpt

    return summary


def _sanitized_body_excerpt(raw_body: str | None) -> str | None:
    if raw_body is None:
        return None
    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError:
        sanitized_text = _redact_secret_values(raw_body)
        return sanitized_text[:_BODY_EXCERPT_LIMIT]
    return json.dumps(_sanitize_debug_value(parsed), separators=(",", ":"))[:_BODY_EXCERPT_LIMIT]


def _sanitize_debug_value(value: Any, key: str | None = None) -> Any:
    normalized_key = (key or "").lower().replace("-", "_")
    if _is_secret_like_key(normalized_key):
        return "[filtered]"
    if isinstance(value, dict):
        return {
            item_key: _sanitize_debug_value(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_debug_value(item) for item in value]
    if isinstance(value, str):
        return _redact_secret_values(value)
    return value


def _is_secret_like_key(normalized_key: str) -> bool:
    if normalized_key in _ALLOWED_USAGE_COUNTERS:
        return False
    return any(
        fragment in normalized_key
        for fragment in (
            "api_key",
            "apikey",
            "authorization",
            "auth",
            "bearer",
            "header",
            "secret",
            "password",
            "token",
        )
    )


def _redact_secret_values(value: str) -> str:
    redacted = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [filtered]", value)
    return re.sub(r"sk-[A-Za-z0-9._~+/=-]+", "sk-[filtered]", redacted)
