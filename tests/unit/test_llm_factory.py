from __future__ import annotations

import pytest

from sprintpilot.llm import (
    LLMProvider,
    LLMProviderConfig,
    LLMRequest,
    LLMResponse,
    UnsupportedProviderError,
    create_provider,
    register_provider,
)


class StubProvider(LLMProvider):
    def __init__(self, config: LLMProviderConfig) -> None:
        self._config = config

    @property
    def config(self) -> LLMProviderConfig:
        return self._config

    def execute(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content=request.messages[-1].content, model=self._config.model_name)


def test_factory_returns_registered_provider() -> None:
    config = LLMProviderConfig(provider_name="stub", model_name="stub-model")

    provider = create_provider(config, registry={"stub": StubProvider})

    assert isinstance(provider, StubProvider)
    assert provider.config is config


def test_factory_rejects_unsupported_provider() -> None:
    config = LLMProviderConfig(provider_name="missing", model_name="model")

    with pytest.raises(UnsupportedProviderError) as exc_info:
        create_provider(config, registry={})

    assert "missing" in str(exc_info.value)


def test_register_provider_adds_provider_to_registry() -> None:
    registry: dict[str, type[LLMProvider]] = {}

    register_provider("stub", StubProvider, registry=registry)

    assert registry["stub"] is StubProvider
