from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from urllib.error import HTTPError

import pytest

from sprintpilot.llm import LLMExecutionError, LLMProviderConfig, LLMRequest, Message, create_provider
from sprintpilot.llm.providers.openrouter import OpenRouterProvider, OpenRouterProviderError
from sprintpilot.workflow.core import (
    run_architecture_planning_workflow,
    run_confidence_assessment_workflow,
    run_product_definition_workflow,
    run_sprint_planning_workflow,
)


class FakeHttpResponse:
    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_default_factory_creates_openrouter_provider() -> None:
    config = LLMProviderConfig(provider_name="openrouter", model_name="openrouter/free")

    provider = create_provider(config)

    assert isinstance(provider, OpenRouterProvider)
    assert provider.config is config


def test_openrouter_execute_maps_chat_completion_request_and_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: float | None = None) -> FakeHttpResponse:
        captured["url"] = request.full_url
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeHttpResponse(
            {
                "model": "openrouter/free",
                "choices": [
                    {
                        "message": {"content": '{"summary": "ok"}'},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
                "id": "gen-test",
            }
        )

    monkeypatch.setattr("sprintpilot.llm.providers.openrouter.urlopen", fake_urlopen)
    provider = OpenRouterProvider(
        LLMProviderConfig(
            provider_name="openrouter",
            model_name="openai/gpt-oss-20b:free",
            fallback_models=[
                "meta-llama/llama-3.3-70b-instruct:free",
                "nousresearch/hermes-3-llama-3.1-405b:free",
            ],
            timeout_seconds=12,
            environment_keys=["OPENROUTER_API_KEY"],
        )
    )

    response = provider.execute(
        LLMRequest(
            messages=[
                Message(role="system", content="Return JSON only."),
                Message(role="user", content="Plan a tiny app."),
            ],
            temperature=0.2,
            max_tokens=512,
            response_schema={"name": "ProductDefinition", "type": "object"},
        )
    )

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["timeout"] == 12
    assert captured["headers"]["Authorization"] == "Bearer test-openrouter-key"
    assert captured["headers"]["Content-type"] == "application/json"
    assert captured["body"] == {
        "model": "openai/gpt-oss-20b:free",
        "models": [
            "meta-llama/llama-3.3-70b-instruct:free",
            "nousresearch/hermes-3-llama-3.1-405b:free",
        ],
        "messages": [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": "Plan a tiny app."},
        ],
            "temperature": 0.2,
            "max_tokens": 512,
            "reasoning": {"enabled": False, "exclude": True},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                "name": "ProductDefinition",
                "strict": True,
                "schema": {"name": "ProductDefinition", "type": "object"},
            },
        },
    }
    assert response.content == '{"summary": "ok"}'
    assert response.model == "openrouter/free"
    assert response.finish_reason == "stop"
    assert response.usage["total_tokens"] == 8
    assert response.raw_metadata["id"] == "gen-test"


def test_openrouter_request_omits_models_when_no_fallbacks_are_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: float | None = None) -> FakeHttpResponse:
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeHttpResponse(
            {
                "model": "openai/gpt-oss-20b:free",
                "choices": [{"message": {"content": '{"summary": "ok"}'}, "finish_reason": "stop"}],
            }
        )

    monkeypatch.setattr("sprintpilot.llm.providers.openrouter.urlopen", fake_urlopen)
    provider = OpenRouterProvider(
        LLMProviderConfig(
            provider_name="openrouter",
            model_name="openai/gpt-oss-20b:free",
            environment_keys=["OPENROUTER_API_KEY"],
        )
    )

    provider.execute(LLMRequest(messages=[Message(role="user", content="hello")]))

    assert "models" not in captured["body"]


def test_openrouter_response_mapping_sanitizes_usage_and_raw_metadata() -> None:
    provider = OpenRouterProvider(
        LLMProviderConfig(provider_name="openrouter", model_name="openrouter/free")
    )

    response = provider._response_from_completion(
        {
            "id": "gen-test",
            "model": "openrouter/free",
            "choices": [
                {
                    "message": {"content": '{"summary": "ok"}'},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 3,
                "completion_tokens": 5,
                "total_tokens": 8,
                "cached_tokens": 2,
                "api_key": "sk-secret",
                "bearer_auth": "Bearer secret",
                "request_headers": {"Authorization": "Bearer secret"},
                "tokens": ["not", "a", "counter"],
                "secret": "hidden",
            },
            "request_headers": {"Authorization": "Bearer secret"},
            "raw_provider_payload": {"api_key": "sk-secret"},
            "authorization": "Bearer secret",
        }
    )

    assert response.usage == {
        "prompt_tokens": 3,
        "completion_tokens": 5,
        "total_tokens": 8,
        "cached_tokens": 2,
    }
    assert response.raw_metadata == {"id": "gen-test"}


def test_openrouter_missing_choices_with_error_object_raises_clear_provider_error() -> None:
    provider = OpenRouterProvider(
        LLMProviderConfig(provider_name="openrouter", model_name="openrouter/free")
    )

    with pytest.raises(OpenRouterProviderError) as exc_info:
        provider._response_from_completion(
            {
                "id": "gen-error",
                "error": {
                    "message": "No endpoints found that support tool use",
                    "code": 404,
                    "metadata": {"api_key": "sk-secret", "headers": {"Authorization": "Bearer secret"}},
                },
            },
            http_status=200,
            raw_body='{"id":"gen-error","error":{"message":"No endpoints found that support tool use","metadata":{"api_key":"sk-secret"}}}',
        )

    error = exc_info.value
    assert "OpenRouter did not return a usable chat completion" in str(error)
    assert "No endpoints found that support tool use" in str(error)
    assert "sk-secret" not in str(error)
    assert error.debug_summary == {
        "http_status": 200,
        "response_id": "gen-error",
        "error_message": "No endpoints found that support tool use",
        "body_excerpt": '{"id":"gen-error","error":{"message":"No endpoints found that support tool use","metadata":{"api_key":"[filtered]"}}}',
    }


def test_openrouter_missing_choices_without_error_object_raises_clear_provider_error() -> None:
    provider = OpenRouterProvider(
        LLMProviderConfig(provider_name="openrouter", model_name="openrouter/free")
    )

    with pytest.raises(OpenRouterProviderError) as exc_info:
        provider._response_from_completion(
            {"id": "gen-empty", "model": "openrouter/free", "usage": {"total_tokens": 0}},
            http_status=200,
            raw_body='{"id":"gen-empty","model":"openrouter/free","usage":{"total_tokens":0}}',
        )

    error = exc_info.value
    assert "missing choices" in str(error).lower()
    assert error.debug_summary["http_status"] == 200
    assert error.debug_summary["response_id"] == "gen-empty"
    assert error.debug_summary["body_excerpt"] == (
        '{"id":"gen-empty","model":"openrouter/free","usage":{"total_tokens":0}}'
    )


def test_openrouter_retries_transient_http_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    attempts = 0

    def fake_urlopen(request: Any, timeout: float | None = None) -> FakeHttpResponse:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise HTTPError(url=request.full_url, code=503, msg="Service Unavailable", hdrs=None, fp=None)
        return FakeHttpResponse(
            {
                "model": "deepseek/deepseek-chat-v3-0324:free",
                "choices": [{"message": {"content": '{"summary": "ok"}'}, "finish_reason": "stop"}],
                "usage": {"total_tokens": 8},
            },
            status=200,
        )

    monkeypatch.setattr("sprintpilot.llm.providers.openrouter.urlopen", fake_urlopen)
    provider = OpenRouterProvider(
        LLMProviderConfig(
            provider_name="openrouter",
            model_name="deepseek/deepseek-chat-v3-0324:free",
            max_retries=1,
            environment_keys=["OPENROUTER_API_KEY"],
        )
    )

    response = provider.execute(LLMRequest(messages=[Message(role="user", content="hello")]))

    assert attempts == 2
    assert response.model == "deepseek/deepseek-chat-v3-0324:free"


def test_openrouter_retry_delay_respects_retry_after_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    sleep_calls: list[float] = []
    attempts = 0

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    def fake_urlopen(request: Any, timeout: float | None = None) -> FakeHttpResponse:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise HTTPError(
                url=request.full_url,
                code=429,
                msg="Too Many Requests",
                hdrs={"Retry-After": "3"},
                fp=None,
            )
        return FakeHttpResponse(
            {
                "model": "openai/gpt-oss-20b:free",
                "choices": [{"message": {"content": '{"summary": "ok"}'}, "finish_reason": "stop"}],
            }
        )

    monkeypatch.setattr("sprintpilot.llm.providers.openrouter.sleep", fake_sleep)
    monkeypatch.setattr("sprintpilot.llm.providers.openrouter.urlopen", fake_urlopen)
    provider = OpenRouterProvider(
        LLMProviderConfig(
            provider_name="openrouter",
            model_name="openai/gpt-oss-20b:free",
            max_retries=1,
            environment_keys=["OPENROUTER_API_KEY"],
        )
    )

    provider.execute(LLMRequest(messages=[Message(role="user", content="hello")]))

    assert sleep_calls == [3]


def test_openrouter_execute_wraps_http_errors_without_echoing_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-openrouter-key")

    def fake_urlopen(request: Any, timeout: float | None = None) -> FakeHttpResponse:
        raise HTTPError(
            url=request.full_url,
            code=401,
            msg="Unauthorized secret-openrouter-key",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("sprintpilot.llm.providers.openrouter.urlopen", fake_urlopen)
    provider = OpenRouterProvider(
        LLMProviderConfig(
            provider_name="openrouter",
            model_name="openrouter/free",
            environment_keys=["OPENROUTER_API_KEY"],
        )
    )

    with pytest.raises(LLMExecutionError) as exc_info:
        provider.execute(LLMRequest(messages=[Message(role="user", content="hello")]))

    assert "401" in str(exc_info.value)
    assert "secret-openrouter-key" not in str(exc_info.value)


def test_openrouter_429_error_includes_upstream_provider_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    error_body = json.dumps(
        {
            "error": {
                "message": "Provider returned error",
                "code": 429,
                "metadata": {
                    "raw": "qwen/qwen3-coder:free is temporarily rate-limited upstream.",
                    "headers": {"Authorization": "Bearer secret"},
                },
            }
        }
    ).encode("utf-8")

    def fake_urlopen(request: Any, timeout: float | None = None) -> FakeHttpResponse:
        raise HTTPError(
            url=request.full_url,
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=BytesIO(error_body),
        )

    monkeypatch.setattr("sprintpilot.llm.providers.openrouter.urlopen", fake_urlopen)
    provider = OpenRouterProvider(
        LLMProviderConfig(
            provider_name="openrouter",
            model_name="openrouter/free",
            environment_keys=["OPENROUTER_API_KEY"],
        )
    )

    with pytest.raises(OpenRouterProviderError) as exc_info:
        provider.execute(LLMRequest(messages=[Message(role="user", content="hello")]))

    message = str(exc_info.value)
    assert "Provider returned error" in message
    assert "temporarily rate-limited upstream" in message
    assert "Bearer secret" not in message


class MockedOpenRouterProvider(OpenRouterProvider):
    def execute(self, request: LLMRequest):  # type: ignore[no-untyped-def]
        schema_name = (request.response_schema or {}).get("name")
        payloads = {
            "ProductDefinition": _product_definition_payload(),
            "ArchitecturePlan": _architecture_plan_payload(),
            "SprintPlan": _sprint_plan_payload(),
        }
        return super()._response_from_completion(
            {
                "model": self.config.model_name,
                "choices": [{"message": {"content": json.dumps(payloads[schema_name])}, "finish_reason": "stop"}],
                "usage": {"total_tokens": 1},
            }
        )


def test_core_v1_workflow_runs_through_openrouter_provider_boundary_without_network() -> None:
    provider = MockedOpenRouterProvider(
        LLMProviderConfig(provider_name="openrouter", model_name="openrouter/free")
    )

    product_definition = run_product_definition_workflow(
        product_idea="Build a student internship tracking platform.",
        provider=provider,
    )
    architecture_plan = run_architecture_planning_workflow(
        product_definition=product_definition,
        provider=provider,
    )
    sprint_plan = run_sprint_planning_workflow(
        product_definition=product_definition,
        architecture_plan=architecture_plan,
        provider=provider,
    )
    assessment = run_confidence_assessment_workflow(
        product_definition=product_definition,
        architecture_plan=architecture_plan,
        sprint_plan=sprint_plan,
    )

    assert product_definition.summary
    assert architecture_plan.recommended_architecture
    assert sprint_plan.story_point_estimates[0].reasoning
    assert assessment.overall_score >= 0


def _product_definition_payload() -> dict[str, object]:
    return {
        "summary": "A student internship tracking platform for organizing applications and progress.",
        "primary_users": ["students", "career advisors"],
        "functional_requirements": [
            {"id": "FR-001", "text": "System must let students record internship applications."},
            {"id": "FR-002", "text": "System must track each application status."},
        ],
        "non_functional_requirements": [
            {"id": "NFR-001", "text": "Outputs must be easy for students to review."}
        ],
        "user_stories": [
            {
                "id": "US-001",
                "title": "Track internship application",
                "priority": "P1",
                "actor": "student",
                "goal": "record an internship application",
                "benefit": "monitor progress and next steps",
                "acceptance_criteria": [
                    {
                        "given": "a student has internship details",
                        "when": "they add the application",
                        "then": "the application appears with a status",
                    }
                ],
            }
        ],
        "assumptions": [{"text": "Students manage one personal application list."}],
        "missing_information": [
            {"question": "Should advisors view student data?", "impact": "Affects permissions and scope."}
        ],
        "reasoning": {"summary": "The idea centers on reducing application-tracking ambiguity."},
    }


def _architecture_plan_payload() -> dict[str, object]:
    return {
        "recommended_architecture": "A modular local application with separated domain and workflow boundaries.",
        "technology_stack_categories": [
            {"name": "Interface", "recommendation": "Local workflow surface", "rationale": "Keeps Core v1 focused."}
        ],
        "system_components": [
            {"name": "Application Tracker Domain", "responsibility": "Represent applications and statuses."}
        ],
        "database_considerations": "A simple persistent store may be needed in a later product implementation.",
        "tradeoffs": [
            {
                "decision": "Keep planning local and modular.",
                "benefit": "Avoids premature integration complexity.",
                "cost": "Does not solve collaboration in Core v1.",
            }
        ],
        "assumptions": [{"text": "The first product version focuses on individual student tracking."}],
        "open_questions": [
            {"question": "Are reminders required?", "impact": "Could affect scheduling components."}
        ],
        "risks": [{"description": "Ambiguous advisor access could change architecture scope."}],
        "reasoning": {"summary": "The architecture separates planning concerns."},
    }


def _sprint_plan_payload() -> dict[str, object]:
    return {
        "epics": [
            {"id": "EPIC-001", "title": "Application Tracking", "objective": "Help students track applications."}
        ],
        "stories": [
            {
                "id": "SP-001",
                "title": "Record internship application",
                "priority": "P1",
                "acceptance_criteria": [
                    "Given internship details, when a student records them, then the application is saved."
                ],
            }
        ],
        "tasks": [
            {"id": "TASK-001", "story_id": "SP-001", "description": "Define application fields and statuses."}
        ],
        "story_point_estimates": [
            {"story_id": "SP-001", "points": 3, "reasoning": "A small first slice with clear acceptance criteria."}
        ],
        "dependencies": [
            {"description": "Status vocabulary must be agreed before task breakdown.", "impacts": ["SP-001"]}
        ],
        "assumptions": [{"text": "The first sprint targets manual application tracking only."}],
        "risks": [{"description": "Reminder features could expand scope if included too early."}],
        "reasoning": {"summary": "The sprint plan prioritizes a minimal increment."},
    }
