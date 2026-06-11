from __future__ import annotations

from sprintpilot.llm import (
    LLMExecutionError,
    LLMProviderError,
    StructuredOutputError,
    UnsupportedProviderError,
)


def test_provider_exceptions_share_common_base() -> None:
    assert issubclass(UnsupportedProviderError, LLMProviderError)
    assert issubclass(LLMExecutionError, LLMProviderError)
    assert issubclass(StructuredOutputError, LLMProviderError)


def test_execution_error_preserves_provider_and_message() -> None:
    error = LLMExecutionError("request failed", provider_name="stub")

    assert error.provider_name == "stub"
    assert "request failed" in str(error)
    assert "stub" in str(error)
