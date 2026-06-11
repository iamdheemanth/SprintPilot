from __future__ import annotations

from sprintpilot.domain import ProductIdea
from sprintpilot.llm import LLMProvider, LLMProviderConfig, LLMRequest, LLMResponse, StructuredGenerationResult
from sprintpilot.workflow.core import normalize_product_idea, run_product_definition_workflow


class ProductDefinitionProvider(LLMProvider):
    @property
    def config(self) -> LLMProviderConfig:
        return LLMProviderConfig(provider_name="test", model_name="test-model")

    def execute(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content="{}")

    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        return StructuredGenerationResult(
            data={
                "summary": "A planning assistant for founders.",
                "primary_users": ["founders"],
                "functional_requirements": [
                    {"id": "FR-001", "text": "System must accept a product idea."}
                ],
                "non_functional_requirements": [
                    {"id": "NFR-001", "text": "Outputs must include reasoning."}
                ],
                "user_stories": [
                    {
                        "id": "US-001",
                        "title": "Capture idea",
                        "priority": "P1",
                        "actor": "founder",
                        "goal": "enter a product idea",
                        "benefit": "receive a product definition",
                        "acceptance_criteria": [
                            {
                                "given": "a product idea",
                                "when": "planning is requested",
                                "then": "a product definition is generated",
                            }
                        ],
                    }
                ],
                "reasoning": {"summary": "Product definition is the first workflow step."},
            },
            raw_response=LLMResponse(content="{}"),
        )


def test_normalize_product_idea_accepts_text() -> None:
    idea = normalize_product_idea("  Build a planning assistant  ")

    assert isinstance(idea, ProductIdea)
    assert idea.raw_text == "Build a planning assistant"


def test_product_definition_workflow_uses_llm_provider_boundary() -> None:
    definition = run_product_definition_workflow(
        product_idea="Build a planning assistant",
        provider=ProductDefinitionProvider(),
    )

    assert definition.summary == "A planning assistant for founders."
    assert definition.review_required is True
