"""Provider interface for SprintPilot LLM integrations."""

from __future__ import annotations

import json
from time import perf_counter
from abc import ABC, abstractmethod
from typing import Any

from sprintpilot.llm.exceptions import LLMProviderError, StructuredOutputError
from sprintpilot.llm.models import (
    LLMProviderConfig,
    LLMProviderHealthCheckResult,
    LLMRequest,
    LLMResponse,
    Message,
    StructuredGenerationResult,
)


class LLMProvider(ABC):
    """Provider-agnostic interface consumed by higher-level SprintPilot code."""

    @property
    @abstractmethod
    def config(self) -> LLMProviderConfig:
        """Return provider-neutral runtime configuration."""

    @abstractmethod
    def execute(self, request: LLMRequest) -> LLMResponse:
        """Execute a prompt request and return a provider-neutral response."""

    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        """Execute a request and parse the response as structured JSON data."""

        response = self.execute(request)
        try:
            data: Any = json.loads(response.content)
        except json.JSONDecodeError as exc:
            return StructuredGenerationResult(
                data=None,
                raw_response=response,
                validation_errors=[f"response was not valid JSON: {exc.msg}"],
            )

        if request.response_schema and not isinstance(data, dict):
            raise StructuredOutputError(
                "structured generation expected an object response",
                provider_name=self.config.provider_name,
            )

        return StructuredGenerationResult(data=data, raw_response=response, validation_errors=[])

    def check_health(self) -> LLMProviderHealthCheckResult:
        """Run a minimal structured-output health check through the provider."""

        started_at = perf_counter()
        request = LLMRequest(
            messages=[
                Message(
                    role="system",
                    content="Return JSON only. Follow the supplied schema exactly.",
                ),
                Message(role="user", content='{"status":"ok"}'),
            ],
            temperature=0,
            max_tokens=512,
            response_schema={
                "name": "SprintPilotProviderHealthCheck",
                "schema": {
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                    "required": ["status"],
                    "additionalProperties": False,
                },
            },
        )
        try:
            result = self.generate_structured(request)
        except LLMProviderError as exc:
            return LLMProviderHealthCheckResult(
                request_sent=True,
                response_received=False,
                structured_output_supported=False,
                elapsed_ms=_elapsed_ms(started_at),
                provider_error=str(exc),
                error_message=_debug_error_message(exc),
                http_status=_debug_http_status(exc),
                response_id=_debug_response_id(exc),
            )

        metadata = result.raw_response.raw_metadata
        return LLMProviderHealthCheckResult(
            request_sent=True,
            response_received=True,
            structured_output_supported=result.is_valid and isinstance(result.data, dict),
            elapsed_ms=_elapsed_ms(started_at),
            http_status=_metadata_int(metadata, "http_status"),
            response_id=_metadata_str(metadata, "id"),
            error_message="; ".join(result.validation_errors) if result.validation_errors else None,
        )


def _elapsed_ms(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))


def _debug_summary(exc: LLMProviderError) -> dict[str, Any]:
    summary = getattr(exc, "debug_summary", None)
    return summary if isinstance(summary, dict) else {}


def _debug_http_status(exc: LLMProviderError) -> int | None:
    value = _debug_summary(exc).get("http_status")
    return value if isinstance(value, int) else None


def _debug_response_id(exc: LLMProviderError) -> str | None:
    value = _debug_summary(exc).get("response_id")
    return value if isinstance(value, str) else None


def _debug_error_message(exc: LLMProviderError) -> str | None:
    value = _debug_summary(exc).get("error_message")
    return value if isinstance(value, str) else None


def _metadata_int(metadata: dict[str, Any], key: str) -> int | None:
    value = metadata.get(key)
    return value if isinstance(value, int) else None


def _metadata_str(metadata: dict[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    return value if isinstance(value, str) else None
