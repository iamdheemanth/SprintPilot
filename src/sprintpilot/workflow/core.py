"""Core v1 workflow orchestration for product definition only."""

from __future__ import annotations

from pathlib import Path

from sprintpilot.agents.crew import (
    create_architect_crew,
    create_product_manager_crew,
    create_scrum_master_crew,
)
from sprintpilot.domain import (
    ArchitecturePlan,
    EngineeringConfidenceAssessment,
    ProductDefinition,
    ProductIdea,
    SprintPlan,
)
from sprintpilot.llm import LLMProvider
from sprintpilot.scoring import assess_engineering_confidence


def normalize_product_idea(
    product_idea: str | ProductIdea,
    *,
    idea_file: str | Path | None = None,
) -> ProductIdea:
    """Normalize text or file input into a ProductIdea."""

    if isinstance(product_idea, ProductIdea):
        return product_idea
    if idea_file is not None:
        text = Path(idea_file).read_text(encoding="utf-8")
        return ProductIdea(raw_text=text)
    return ProductIdea(raw_text=product_idea)


def run_product_definition_workflow(
    *,
    product_idea: str | ProductIdea,
    provider: LLMProvider,
) -> ProductDefinition:
    """Run only the Product Manager product-definition workflow."""

    idea = normalize_product_idea(product_idea)
    parsed = create_product_manager_crew(provider).run(idea)
    if not parsed.is_valid or parsed.value is None:
        joined_errors = "; ".join(parsed.validation_errors) or "unknown validation error"
        raise ValueError(f"Product definition generation failed: {joined_errors}")
    return parsed.value


def run_architecture_planning_workflow(
    *,
    product_definition: ProductDefinition,
    provider: LLMProvider,
) -> ArchitecturePlan:
    """Run only the Architect architecture-planning workflow."""

    parsed = create_architect_crew(provider).run(product_definition)
    if not parsed.is_valid or parsed.value is None:
        joined_errors = "; ".join(parsed.validation_errors) or "unknown validation error"
        raise ValueError(f"Architecture planning failed: {joined_errors}")
    return parsed.value


def run_sprint_planning_workflow(
    *,
    product_definition: ProductDefinition,
    architecture_plan: ArchitecturePlan,
    provider: LLMProvider,
) -> SprintPlan:
    """Run only the Scrum Master sprint-planning workflow."""

    parsed = create_scrum_master_crew(provider).run(
        product_definition=product_definition,
        architecture_plan=architecture_plan,
    )
    if not parsed.is_valid or parsed.value is None:
        joined_errors = "; ".join(parsed.validation_errors) or "unknown validation error"
        raise ValueError(f"Sprint planning failed: {joined_errors}")
    return parsed.value


def run_confidence_assessment_workflow(
    *,
    product_definition: ProductDefinition,
    architecture_plan: ArchitecturePlan,
    sprint_plan: SprintPlan,
) -> EngineeringConfidenceAssessment:
    """Run only the deterministic Engineering Confidence Score workflow."""

    return assess_engineering_confidence(
        product_definition=product_definition,
        architecture_plan=architecture_plan,
        sprint_plan=sprint_plan,
    )
