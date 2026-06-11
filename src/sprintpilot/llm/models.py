"""Provider-neutral request and response models for LLM execution."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MessageRole = Literal["system", "user", "assistant", "tool"]


def _reject_secret_like_mapping(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not value:
        return value

    blocked_fragments = ("api_key", "apikey", "secret", "password")
    allowed_token_usage_keys = {
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "cached_tokens",
        "reasoning_tokens",
        "audio_tokens",
        "video_tokens",
        "image_tokens",
    }
    for key in value:
        normalized = key.lower().replace("-", "_")
        if normalized in allowed_token_usage_keys:
            continue
        if "token" in normalized:
            raise ValueError("provider-neutral metadata must not contain secret-like keys")
        if any(fragment in normalized for fragment in blocked_fragments):
            raise ValueError("provider-neutral metadata must not contain secret-like keys")
    return value


class Message(BaseModel):
    """Provider-independent prompt message."""

    model_config = ConfigDict(extra="forbid")

    role: MessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message content must not be empty")
        return value

    @field_validator("metadata")
    @classmethod
    def metadata_must_not_include_secrets(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _reject_secret_like_mapping(value) or {}


class LLMRequest(BaseModel):
    """Provider-independent prompt execution request."""

    model_config = ConfigDict(extra="forbid")

    messages: list[Message]
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    response_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("messages")
    @classmethod
    def messages_must_not_be_empty(cls, value: list[Message]) -> list[Message]:
        if not value:
            raise ValueError("llm request must include at least one message")
        return value

    @field_validator("metadata")
    @classmethod
    def metadata_must_not_include_secrets(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _reject_secret_like_mapping(value) or {}


class LLMResponse(BaseModel):
    """Provider-independent prompt execution response."""

    model_config = ConfigDict(extra="forbid")

    content: str
    model: str | None = None
    finish_reason: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("usage", "raw_metadata")
    @classmethod
    def mappings_must_not_include_secrets(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _reject_secret_like_mapping(value) or {}


class StructuredGenerationResult(BaseModel):
    """Parsed structured generation result with the raw response preserved."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    data: Any | None = None
    raw_response: LLMResponse
    validation_errors: list[str] = Field(default_factory=list)
    is_valid: bool = True

    @model_validator(mode="after")
    def derive_validity_from_errors(self) -> "StructuredGenerationResult":
        self.is_valid = not self.validation_errors
        return self


class LLMProviderHealthCheckResult(BaseModel):
    """Provider-neutral diagnostics from a minimal health check request."""

    model_config = ConfigDict(extra="forbid")

    request_sent: bool = False
    response_received: bool = False
    structured_output_supported: bool = False
    elapsed_ms: int = Field(default=0, ge=0)
    http_status: int | None = Field(default=None, ge=100, le=599)
    response_id: str | None = None
    provider_error: str | None = None
    error_message: str | None = None

    @field_validator("response_id", "provider_error", "error_message")
    @classmethod
    def optional_text_must_not_include_secrets(cls, value: str | None) -> str | None:
        if value is None:
            return value
        _reject_secret_like_mapping({"diagnostic": value})
        return value


class LLMProviderConfig(BaseModel):
    """Provider-neutral runtime configuration for the LLM factory."""

    model_config = ConfigDict(extra="forbid")

    provider_name: str
    model_name: str
    fallback_models: list[str] = Field(default_factory=list)
    timeout_seconds: float | None = Field(default=None, gt=0)
    max_retries: int = Field(default=0, ge=0)
    environment_keys: list[str] = Field(default_factory=list)

    @field_validator("provider_name", "model_name")
    @classmethod
    def required_strings_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("provider configuration values must not be empty")
        return value

    @field_validator("fallback_models")
    @classmethod
    def fallback_models_must_be_model_names(cls, value: list[str]) -> list[str]:
        normalized_models: list[str] = []
        for model in value:
            normalized = model.strip()
            if not normalized:
                raise ValueError("fallback model names must not be empty")
            if normalized.startswith(("sk-", "sk_", "Bearer ")):
                raise ValueError("fallback_models must contain model names, not secret values")
            normalized_models.append(normalized)
        return normalized_models

    @field_validator("environment_keys")
    @classmethod
    def environment_keys_must_be_names(cls, value: list[str]) -> list[str]:
        for key in value:
            normalized = key.strip()
            if not normalized:
                raise ValueError("environment key names must not be empty")
            if normalized.startswith(("sk-", "sk_", "Bearer ")):
                raise ValueError("environment_keys must contain variable names, not secret values")
        return value
