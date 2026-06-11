from __future__ import annotations

from tests.unit.test_product_definition_models import _story

from sprintpilot.agents.prompts import build_architect_messages
from sprintpilot.domain import ProductDefinition, ProductRequirement, Reasoning


def _definition() -> ProductDefinition:
    return ProductDefinition(
        summary="A planning assistant for founders.",
        primary_users=["founders"],
        functional_requirements=[ProductRequirement(id="FR-001", text="System must accept a product idea.")],
        non_functional_requirements=[ProductRequirement(id="NFR-001", text="Outputs must include reasoning.")],
        user_stories=[_story()],
        reasoning=Reasoning(summary="Product definition is the first planning artifact."),
    )


def test_architect_prompt_uses_core_v1_scope_and_architecture_terms() -> None:
    messages = build_architect_messages(_definition())
    prompt_text = "\n".join(message.content for message in messages)

    assert "Architect Agent" in prompt_text
    assert "recommended architecture" in prompt_text
    assert "technology stack categories" in prompt_text
    assert "high-level system components" in prompt_text
    assert "database considerations" in prompt_text
    assert "tradeoffs" in prompt_text
    assert "Do not generate source code" in prompt_text
    assert "A planning assistant for founders." in messages[-1].content


def test_architect_prompt_explicitly_excludes_analytics_and_deployment_scope() -> None:
    definition = _definition().model_copy(
        update={
            "summary": "A student internship tracker with application analytics for students.",
            "functional_requirements": [
                ProductRequirement(
                    id="FR-001",
                    text="System must show application analytics to students.",
                )
            ],
        }
    )

    messages = build_architect_messages(definition)
    prompt_text = "\n".join(message.content for message in messages)

    assert "only produce system components, stack categories, database considerations" in prompt_text
    assert "Do not introduce analytics modules" in prompt_text
    assert "deployment concerns" in prompt_text
    assert "CI/CD" in prompt_text
    assert "cloud hosting" in prompt_text
    assert "release engineering" in prompt_text
    assert "observability dashboards" in prompt_text
    assert "application analytics" in prompt_text
    assert "product concept only" in prompt_text
    assert "Do not mention analytics" in prompt_text
    assert "Do not mention deployment" in prompt_text
    assert "Do not mention multi-user" in prompt_text
    assert "Product definition summary:\nA student internship tracker for students." in messages[-1].content
    assert "FR-001: System must show application analytics to students." not in messages[-1].content
    assert "Intentionally excluded from Core v1 architecture scope" in messages[-1].content
