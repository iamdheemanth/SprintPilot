from __future__ import annotations

import pytest
from pydantic import ValidationError

from sprintpilot.domain import (
    ArchitecturePlan,
    ArchitectureTradeoff,
    Assumption,
    MissingInformation,
    Reasoning,
    Risk,
    StackCategory,
    SystemComponent,
)


def test_architecture_plan_requires_components_tradeoffs_and_reasoning() -> None:
    with pytest.raises(ValidationError):
        ArchitecturePlan(
            recommended_architecture="Small modular CLI application.",
            technology_stack_categories=[],
            system_components=[],
            tradeoffs=[],
            assumptions=[],
            open_questions=[],
            reasoning=Reasoning(summary=""),
        )


def test_architecture_plan_preserves_reviewable_guidance_sections() -> None:
    plan = ArchitecturePlan(
        recommended_architecture="Use a modular local CLI with separate domain and orchestration layers.",
        technology_stack_categories=[
            StackCategory(name="Interface", recommendation="CLI", rationale="Smallest viable v1 surface.")
        ],
        system_components=[
            SystemComponent(
                name="Workflow Service",
                responsibility="Coordinate product definition and architecture planning.",
            )
        ],
        database_considerations="No database is required for Core v1.",
        tradeoffs=[
            ArchitectureTradeoff(
                decision="Use local files instead of a database.",
                benefit="Keeps Core v1 simple.",
                cost="No historical project management.",
            )
        ],
        assumptions=[Assumption(text="The user runs SprintPilot locally.")],
        open_questions=[
            MissingInformation(question="Which model provider is configured?", impact="Affects runtime setup.")
        ],
        risks=[Risk(description="Provider output may be incomplete.")],
        reasoning=Reasoning(summary="The architecture follows Core v1 scope and modularity."),
    )

    assert plan.review_required is True
    assert plan.system_components[0].name == "Workflow Service"
    assert plan.tradeoffs[0].benefit == "Keeps Core v1 simple."
