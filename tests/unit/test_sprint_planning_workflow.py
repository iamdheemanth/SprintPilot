from __future__ import annotations

from tests.unit.test_architect_adapter import _valid_architecture_payload
from tests.unit.test_architect_prompts import _definition
from tests.unit.test_scrum_master_adapter import _valid_sprint_payload

from sprintpilot.domain import ArchitecturePlan, SprintPlan
from sprintpilot.llm import LLMProvider, LLMProviderConfig, LLMRequest, LLMResponse, StructuredGenerationResult
from sprintpilot.workflow.core import run_sprint_planning_workflow


class SprintPlanningProvider(LLMProvider):
    @property
    def config(self) -> LLMProviderConfig:
        return LLMProviderConfig(provider_name="test", model_name="test-model")

    def execute(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content="{}")

    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        return StructuredGenerationResult(
            data=_valid_sprint_payload(),
            raw_response=LLMResponse(content="{}"),
        )


def test_sprint_planning_workflow_uses_llm_provider_boundary() -> None:
    plan = run_sprint_planning_workflow(
        product_definition=_definition(),
        architecture_plan=ArchitecturePlan.model_validate(_valid_architecture_payload()),
        provider=SprintPlanningProvider(),
    )

    assert isinstance(plan, SprintPlan)
    assert plan.review_required is True
    assert plan.story_point_estimates[0].reasoning == "Small workflow with clear scope."
