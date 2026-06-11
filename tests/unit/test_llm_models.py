from __future__ import annotations

import pytest
from pydantic import ValidationError

from sprintpilot.llm import (
    LLMProviderConfig,
    LLMRequest,
    LLMResponse,
    Message,
    StructuredGenerationResult,
)


def test_message_rejects_empty_content() -> None:
    with pytest.raises(ValidationError):
        Message(role="user", content="   ")


def test_llm_request_requires_at_least_one_message() -> None:
    with pytest.raises(ValidationError):
        LLMRequest(messages=[])


def test_llm_request_preserves_provider_neutral_options() -> None:
    request = LLMRequest(
        messages=[Message(role="user", content="Summarize this idea")],
        model="fast-planner",
        temperature=0.2,
        max_tokens=800,
        response_schema={"type": "object"},
        metadata={"stage": "product-definition"},
    )

    assert request.model == "fast-planner"
    assert request.response_schema == {"type": "object"}
    assert request.metadata == {"stage": "product-definition"}


def test_llm_response_rejects_secret_like_usage_keys() -> None:
    with pytest.raises(ValidationError):
        LLMResponse(content="ok", usage={"api_key": "secret"})


def test_llm_response_allows_provider_token_count_usage_keys() -> None:
    response = LLMResponse(
        content="ok",
        usage={"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
    )

    assert response.usage["total_tokens"] == 8


def test_structured_generation_result_tracks_validation_status() -> None:
    response = LLMResponse(content='{"summary": "A planning tool"}')
    result = StructuredGenerationResult(
        data={"summary": "A planning tool"},
        raw_response=response,
        validation_errors=[],
    )

    assert result.is_valid is True
    assert result.raw_response is response


def test_provider_config_stores_environment_key_names_not_secret_values() -> None:
    config = LLMProviderConfig(
        provider_name="test",
        model_name="test-model",
        environment_keys=["SPRINTPILOT_TEST_API_KEY"],
    )

    assert config.provider_name == "test"
    assert config.environment_keys == ["SPRINTPILOT_TEST_API_KEY"]


def test_provider_config_rejects_secret_like_environment_values() -> None:
    with pytest.raises(ValidationError):
        LLMProviderConfig(
            provider_name="test",
            model_name="test-model",
            environment_keys=["sk-this-looks-like-a-secret-value"],
        )
