from __future__ import annotations

from sprintpilot.llm import LLMProvider, LLMProviderConfig, LLMRequest, LLMResponse, Message


class EchoProvider(LLMProvider):
    def __init__(self, config: LLMProviderConfig) -> None:
        self._config = config

    @property
    def config(self) -> LLMProviderConfig:
        return self._config

    def execute(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content=request.messages[-1].content, model=self._config.model_name)


class CapturingHealthProvider(EchoProvider):
    def __init__(self, config: LLMProviderConfig) -> None:
        super().__init__(config)
        self.last_request: LLMRequest | None = None

    def execute(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        return super().execute(request)


def test_provider_interface_supports_prompt_execution() -> None:
    provider = EchoProvider(LLMProviderConfig(provider_name="echo", model_name="echo-model"))
    request = LLMRequest(messages=[Message(role="user", content="hello")])

    response = provider.execute(request)

    assert response.content == "hello"
    assert response.model == "echo-model"


def test_provider_interface_supports_structured_generation() -> None:
    provider = EchoProvider(LLMProviderConfig(provider_name="echo", model_name="echo-model"))
    request = LLMRequest(
        messages=[Message(role="user", content='{"name": "SprintPilot"}')],
        response_schema={"type": "object"},
    )

    result = provider.generate_structured(request)

    assert result.is_valid is True
    assert result.data == {"name": "SprintPilot"}
    assert result.raw_response.content == '{"name": "SprintPilot"}'


def test_provider_interface_default_health_check_reports_structured_output_support() -> None:
    provider = EchoProvider(LLMProviderConfig(provider_name="echo", model_name="echo-model"))

    result = provider.check_health()

    assert result.request_sent is True
    assert result.response_received is True
    assert result.structured_output_supported is True
    assert result.elapsed_ms >= 0


def test_provider_interface_health_check_uses_enough_output_budget_for_free_models() -> None:
    provider = CapturingHealthProvider(LLMProviderConfig(provider_name="echo", model_name="echo-model"))

    provider.check_health()

    assert provider.last_request is not None
    assert provider.last_request.max_tokens == 512
