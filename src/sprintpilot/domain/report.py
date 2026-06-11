"""Structured SprintPilot Core v1 report artifact."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sprintpilot.domain.artifacts import ArchitecturePlan, ProductDefinition, ProductIdea, SprintPlan
from sprintpilot.domain.confidence import EngineeringConfidenceAssessment


CORE_V1_INCLUDED_CAPABILITIES: tuple[str, ...] = (
    "Product idea intake",
    "Product definition",
    "Architecture planning",
    "Sprint planning",
    "Engineering Confidence Score",
    "Structured local report generation",
)

CORE_V1_EXCLUDED_CAPABILITIES: tuple[str, ...] = (
    "GitHub integration",
    "Taiga integration",
    "Code generation or scaffolding",
    "Autonomous coding",
    "Repository management",
    "CI/CD",
    "Analytics",
    "Cloud collaboration",
    "Review agents",
    "RAG systems",
    "Multi-user collaboration",
    "Production deployment concerns",
)


def _strip_required(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be empty")
    return stripped


class SprintPilotReport(BaseModel):
    """Human-reviewable Core v1 report assembled from validated artifacts."""

    model_config = ConfigDict(extra="forbid")

    title: str
    product_idea: ProductIdea
    product_definition: ProductDefinition
    architecture_plan: ArchitecturePlan
    sprint_plan: SprintPlan
    confidence_assessment: EngineeringConfidenceAssessment
    included_capabilities: list[str] = Field(
        default_factory=lambda: list(CORE_V1_INCLUDED_CAPABILITIES)
    )
    excluded_capabilities: list[str] = Field(
        default_factory=lambda: list(CORE_V1_EXCLUDED_CAPABILITIES)
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    review_required: bool = True

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "report title")

    @field_validator("included_capabilities", "excluded_capabilities")
    @classmethod
    def capabilities_must_not_be_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("report scope capabilities must not be empty")
        return [_strip_required(item, "report scope capability") for item in value]
