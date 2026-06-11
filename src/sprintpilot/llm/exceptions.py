"""Exceptions raised by the provider-agnostic LLM layer."""

from __future__ import annotations


class LLMProviderError(Exception):
    """Base exception for LLM provider boundary failures."""

    def __init__(self, message: str, *, provider_name: str | None = None) -> None:
        self.provider_name = provider_name
        if provider_name:
            message = f"{message} [provider={provider_name}]"
        super().__init__(message)


class UnsupportedProviderError(LLMProviderError):
    """Raised when the configured provider has no registered implementation."""


class LLMExecutionError(LLMProviderError):
    """Raised when prompt execution fails inside a provider implementation."""


class StructuredOutputError(LLMProviderError):
    """Raised when structured output generation cannot be completed."""
