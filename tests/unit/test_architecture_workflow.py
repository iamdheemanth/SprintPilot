from __future__ import annotations

from tests.unit.test_architect_adapter import _valid_architecture_payload
from tests.unit.test_architect_prompts import _definition

from sprintpilot.domain import ArchitecturePlan
from sprintpilot.llm import LLMProvider, LLMProviderConfig, LLMRequest, LLMResponse, StructuredGenerationResult
from sprintpilot.workflow.core import run_architecture_planning_workflow


class ArchitectureProvider(LLMProvider):
    @property
    def config(self) -> LLMProviderConfig:
        return LLMProviderConfig(provider_name="test", model_name="test-model")

    def execute(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content="{}")

    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        return StructuredGenerationResult(
            data=_valid_architecture_payload(),
            raw_response=LLMResponse(content="{}"),
        )


class RetryingArchitectureProvider(ArchitectureProvider):
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        self.requests.append(request)
        payload = _valid_architecture_payload()
        if len(self.requests) == 1:
            payload["recommended_architecture"] = (
                "Use deployment automation, observability dashboards and application analytics."
            )
        return StructuredGenerationResult(
            data=payload,
            raw_response=LLMResponse(content="{}"),
        )


class AlwaysOutOfScopeArchitectureProvider(ArchitectureProvider):
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        self.requests.append(request)
        payload = _valid_architecture_payload()
        payload["recommended_architecture"] = (
            "Use a local modular architecture. Add deployment automation and application analytics."
        )
        payload["system_components"] = [
            {
                "name": "Backend API",
                "responsibility": "Coordinate application tracking and analytics dashboards.",
            }
        ]
        payload["tradeoffs"] = [
            {
                "decision": "Local modular architecture with CI/CD.",
                "benefit": "Keeps planning clear while deployment is automated.",
                "cost": "Adds release engineering complexity.",
            }
        ]
        return StructuredGenerationResult(
            data=payload,
            raw_response=LLMResponse(content="{}"),
        )


def test_architecture_workflow_uses_llm_provider_boundary() -> None:
    plan = run_architecture_planning_workflow(
        product_definition=_definition(),
        provider=ArchitectureProvider(),
    )

    assert isinstance(plan, ArchitecturePlan)
    assert plan.review_required is True
    assert plan.tradeoffs[0].decision == "Use local Markdown outputs."


def test_architecture_workflow_retries_when_generated_plan_is_out_of_scope() -> None:
    provider = RetryingArchitectureProvider()

    plan = run_architecture_planning_workflow(
        product_definition=_definition(),
        provider=provider,
    )

    assert isinstance(plan, ArchitecturePlan)
    assert len(provider.requests) == 2
    retry_prompt = "\n".join(message.content for message in provider.requests[1].messages)
    assert "previous architecture output was rejected" in retry_prompt
    assert "Remove analytics" in retry_prompt


def test_architecture_workflow_sanitizes_retry_output_that_still_contains_scope_drift() -> None:
    provider = AlwaysOutOfScopeArchitectureProvider()

    plan = run_architecture_planning_workflow(
        product_definition=_definition(),
        provider=provider,
    )

    serialized = plan.model_dump_json().lower()
    assert "analytics" not in serialized
    assert "deployment" not in serialized
    assert "ci/cd" not in serialized
    assert "release engineering" not in serialized
    assert len(provider.requests) == 2
