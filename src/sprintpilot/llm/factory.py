"""Factory helpers for provider-agnostic LLM implementations."""

from __future__ import annotations

from collections.abc import MutableMapping

from sprintpilot.llm.exceptions import UnsupportedProviderError
from sprintpilot.llm.models import LLMProviderConfig
from sprintpilot.llm.provider import LLMProvider

ProviderRegistry = MutableMapping[str, type[LLMProvider]]

_DEFAULT_REGISTRY: dict[str, type[LLMProvider]] = {}


def register_provider(
    provider_name: str,
    provider_type: type[LLMProvider],
    *,
    registry: ProviderRegistry | None = None,
) -> None:
    """Register a provider implementation by neutral provider name."""

    target_registry = _DEFAULT_REGISTRY if registry is None else registry
    normalized_name = provider_name.strip().lower()
    if not normalized_name:
        raise ValueError("provider name must not be empty")
    target_registry[normalized_name] = provider_type


def create_provider(
    config: LLMProviderConfig,
    *,
    registry: ProviderRegistry | None = None,
) -> LLMProvider:
    """Create the single configured provider for Core v1."""

    source_registry = _DEFAULT_REGISTRY if registry is None else registry
    provider_name = config.provider_name.strip().lower()
    provider_type = source_registry.get(provider_name)
    if provider_type is None:
        raise UnsupportedProviderError(
            f"unsupported LLM provider '{config.provider_name}'",
            provider_name=config.provider_name,
        )
    return provider_type(config)


from sprintpilot.llm.providers.gemini import GeminiProvider
from sprintpilot.llm.providers.openrouter import OpenRouterProvider

register_provider("gemini", GeminiProvider)
register_provider("openrouter", OpenRouterProvider)
