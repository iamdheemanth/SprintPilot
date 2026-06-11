from __future__ import annotations

import pytest
from pydantic import ValidationError

from sprintpilot.domain import (
    AcceptanceCriterion,
    ProductDefinition,
    ProductIdea,
    ProductRequirement,
    Reasoning,
    UserStory,
)


def _story() -> UserStory:
    return UserStory(
        id="US-001",
        title="Capture idea",
        priority="P1",
        actor="founder",
        goal="enter a product idea",
        benefit="receive a structured plan",
        acceptance_criteria=[
            AcceptanceCriterion(
                given="a product idea",
                when="planning is requested",
                then="a product definition is generated",
            )
        ],
    )


def test_product_idea_normalizes_text_and_rejects_blank_input() -> None:
    idea = ProductIdea(raw_text="  Build a planning assistant  ")

    assert idea.raw_text == "Build a planning assistant"

    with pytest.raises(ValidationError):
        ProductIdea(raw_text=" ")


def test_product_definition_requires_functional_requirements_and_user_stories() -> None:
    with pytest.raises(ValidationError):
        ProductDefinition(
            summary="Planning assistant",
            primary_users=["founders"],
            functional_requirements=[],
            non_functional_requirements=[],
            user_stories=[],
            reasoning=Reasoning(summary="Derived from the idea."),
        )


def test_product_definition_preserves_reviewable_sections() -> None:
    definition = ProductDefinition(
        summary="Planning assistant for small teams.",
        primary_users=["founders"],
        functional_requirements=[
            ProductRequirement(id="FR-001", text="System must accept a product idea.")
        ],
        non_functional_requirements=[
            ProductRequirement(id="NFR-001", text="Outputs must include reasoning.")
        ],
        user_stories=[_story()],
        reasoning=Reasoning(summary="The first workflow step clarifies product intent."),
    )

    assert definition.review_required is True
    assert definition.user_stories[0].acceptance_criteria[0].then == "a product definition is generated"
