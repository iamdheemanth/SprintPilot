from __future__ import annotations

import json
import sys
import types
from typing import Any

import pytest

from sprintpilot.llm import LLMExecutionError, LLMProviderConfig, LLMRequest, Message, create_provider


class FakeGenerateContentConfig:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class FakeGeminiClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.models = FakeGeminiModels(self)
        self.calls: list[dict[str, Any]] = []


class FakeGeminiModels:
    def __init__(self, client: FakeGeminiClient) -> None:
        self.client = client

    def generate_content(self, **kwargs: Any) -> Any:
        self.client.calls.append(kwargs)
        return FakeGeminiResponse()


class FakeUsageMetadata:
    prompt_token_count = 7
    candidates_token_count = 11
    total_token_count = 18
    cached_content_token_count = 2
    thoughts_token_count = 3


class FakeCandidate:
    finish_reason = "STOP"


class FakeGeminiResponse:
    text = '{"summary": "ok"}'
    model_version = "gemini-2.5-flash"
    usage_metadata = FakeUsageMetadata()
    candidates = [FakeCandidate()]
    response_id = "gemini-response-1"


@pytest.fixture
def fake_google_genai(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def client_factory(api_key: str) -> FakeGeminiClient:
        client = FakeGeminiClient(api_key)
        captured["client"] = client
        return client

    google_module = types.ModuleType("google")
    genai_module = types.ModuleType("google.genai")
    genai_types_module = types.ModuleType("google.genai.types")
    genai_module.Client = client_factory
    genai_module.types = genai_types_module
    genai_types_module.GenerateContentConfig = FakeGenerateContentConfig
    google_module.genai = genai_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", genai_types_module)
    return captured


def test_default_factory_creates_gemini_provider(fake_google_genai: dict[str, Any]) -> None:
    from sprintpilot.llm.providers.gemini import GeminiProvider

    config = LLMProviderConfig(provider_name="gemini", model_name="gemini-2.5-flash")

    provider = create_provider(config)

    assert isinstance(provider, GeminiProvider)
    assert provider.config is config


def test_gemini_execute_maps_prompt_request_response_schema_and_usage(
    monkeypatch: pytest.MonkeyPatch,
    fake_google_genai: dict[str, Any],
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    from sprintpilot.llm.providers.gemini import GeminiProvider

    provider = GeminiProvider(
        LLMProviderConfig(
            provider_name="gemini",
            model_name="gemini-2.5-flash",
            timeout_seconds=45,
            environment_keys=["GEMINI_API_KEY"],
        )
    )

    response = provider.execute(
        LLMRequest(
            messages=[
                Message(role="system", content="Return JSON only."),
                Message(role="user", content="Plan a tiny app."),
                Message(role="assistant", content="Ask one clarifying question."),
            ],
            temperature=0.1,
            max_tokens=256,
            response_schema={"name": "ProductDefinition", "schema": {"type": "object"}},
        )
    )

    client = fake_google_genai["client"]
    assert client.api_key == "test-gemini-key"
    assert client.calls == [
        {
            "model": "gemini-2.5-flash",
            "contents": [
                {"role": "user", "parts": [{"text": "Plan a tiny app."}]},
                {"role": "model", "parts": [{"text": "Ask one clarifying question."}]},
            ],
            "config": client.calls[0]["config"],
        }
    ]
    config_kwargs = client.calls[0]["config"].kwargs
    assert config_kwargs == {
        "system_instruction": "Return JSON only.",
        "temperature": 0.1,
        "max_output_tokens": 256,
        "response_mime_type": "application/json",
        "response_json_schema": {"type": "object"},
        "http_options": {"timeout": 45000},
    }
    assert response.content == '{"summary": "ok"}'
    assert response.model == "gemini-2.5-flash"
    assert response.finish_reason == "STOP"
    assert response.usage == {
        "prompt_tokens": 7,
        "completion_tokens": 11,
        "total_tokens": 18,
        "cached_tokens": 2,
        "reasoning_tokens": 3,
    }
    assert response.raw_metadata == {"id": "gemini-response-1"}


def test_gemini_generate_structured_maps_valid_json_to_structured_result(
    monkeypatch: pytest.MonkeyPatch,
    fake_google_genai: dict[str, Any],
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    from sprintpilot.llm.providers.gemini import GeminiProvider

    provider = GeminiProvider(
        LLMProviderConfig(provider_name="gemini", model_name="gemini-2.5-flash")
    )

    result = provider.generate_structured(
        LLMRequest(
            messages=[Message(role="user", content="Return a product definition.")],
            response_schema={"name": "ProductDefinition", "schema": {"type": "object"}},
        )
    )

    assert result.is_valid is True
    assert result.data == {"summary": "ok"}
    assert result.raw_response.model == "gemini-2.5-flash"


def test_gemini_structured_output_uses_json_schema_for_standard_schema(
    monkeypatch: pytest.MonkeyPatch,
    fake_google_genai: dict[str, Any],
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    from sprintpilot.llm.providers.gemini import GeminiProvider

    provider = GeminiProvider(
        LLMProviderConfig(provider_name="gemini", model_name="gemini-2.5-flash")
    )

    provider.execute(
        LLMRequest(
            messages=[Message(role="user", content='{"status":"ok"}')],
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
    )

    client = fake_google_genai["client"]
    config_kwargs = client.calls[0]["config"].kwargs
    assert config_kwargs["response_mime_type"] == "application/json"
    assert config_kwargs["response_json_schema"] == {
        "type": "object",
        "properties": {"status": {"type": "string"}},
        "required": ["status"],
        "additionalProperties": False,
    }
    assert "response_schema" not in config_kwargs


def test_gemini_execute_uses_request_model_override(
    monkeypatch: pytest.MonkeyPatch,
    fake_google_genai: dict[str, Any],
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    from sprintpilot.llm.providers.gemini import GeminiProvider

    provider = GeminiProvider(
        LLMProviderConfig(provider_name="gemini", model_name="gemini-2.5-flash")
    )

    provider.execute(
        LLMRequest(
            messages=[Message(role="user", content="hello")],
            model="gemini-2.5-pro",
        )
    )

    client = fake_google_genai["client"]
    assert client.calls[0]["model"] == "gemini-2.5-pro"


def test_gemini_missing_api_key_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch,
    fake_google_genai: dict[str, Any],
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("SPRINTPILOT_GEMINI_API_KEY", raising=False)
    from sprintpilot.llm.providers.gemini import GeminiProvider

    provider = GeminiProvider(
        LLMProviderConfig(provider_name="gemini", model_name="gemini-2.5-flash")
    )

    with pytest.raises(LLMExecutionError) as exc_info:
        provider.execute(LLMRequest(messages=[Message(role="user", content="hello")]))

    assert "GEMINI_API_KEY" in str(exc_info.value)
    assert "SPRINTPILOT_GEMINI_API_KEY" in str(exc_info.value)


def test_gemini_sdk_errors_are_wrapped_without_echoing_api_key(
    monkeypatch: pytest.MonkeyPatch,
    fake_google_genai: dict[str, Any],
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "secret-gemini-key")
    from sprintpilot.llm.providers.gemini import GeminiProvider

    class FailingModels(FakeGeminiModels):
        def generate_content(self, **kwargs: Any) -> Any:
            raise RuntimeError("Unauthorized secret-gemini-key")

    class FailingClient(FakeGeminiClient):
        def __init__(self, api_key: str) -> None:
            super().__init__(api_key)
            self.models = FailingModels(self)

    fake_google_genai["client"] = FailingClient("secret-gemini-key")
    sys.modules["google.genai"].Client = lambda api_key: fake_google_genai["client"]
    provider = GeminiProvider(
        LLMProviderConfig(provider_name="gemini", model_name="gemini-2.5-flash")
    )

    with pytest.raises(LLMExecutionError) as exc_info:
        provider.execute(LLMRequest(messages=[Message(role="user", content="hello")]))

    message = str(exc_info.value)
    assert "Gemini request failed" in message
    assert "secret-gemini-key" not in message


def test_gemini_empty_text_response_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch,
    fake_google_genai: dict[str, Any],
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    from sprintpilot.llm.providers.gemini import GeminiProvider

    class EmptyGeminiResponse(FakeGeminiResponse):
        text = ""

    class EmptyModels(FakeGeminiModels):
        def generate_content(self, **kwargs: Any) -> Any:
            self.client.calls.append(kwargs)
            return EmptyGeminiResponse()

    class EmptyClient(FakeGeminiClient):
        def __init__(self, api_key: str) -> None:
            super().__init__(api_key)
            self.models = EmptyModels(self)

    fake_google_genai["client"] = EmptyClient("test-gemini-key")
    sys.modules["google.genai"].Client = lambda api_key: fake_google_genai["client"]
    provider = GeminiProvider(
        LLMProviderConfig(provider_name="gemini", model_name="gemini-2.5-flash")
    )

    with pytest.raises(LLMExecutionError) as exc_info:
        provider.execute(LLMRequest(messages=[Message(role="user", content="hello")]))

    assert "Gemini response did not include usable text content" in str(exc_info.value)
