"""Domain artifacts for SprintPilot Core v1 product definition."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _strip_required(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be empty")
    return stripped


class Assumption(BaseModel):
    """A stated planning assumption."""

    model_config = ConfigDict(extra="forbid")

    text: str
    source: str | None = None

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "assumption text")


class MissingInformation(BaseModel):
    """Information needed to improve planning confidence."""

    model_config = ConfigDict(extra="forbid")

    question: str
    impact: str

    @field_validator("question", "impact")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "missing information field")


class Risk(BaseModel):
    """A planning or delivery risk."""

    model_config = ConfigDict(extra="forbid")

    description: str
    impact: str | None = None
    mitigation: str | None = None

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "risk description")


class Recommendation(BaseModel):
    """An action recommended to improve readiness."""

    model_config = ConfigDict(extra="forbid")

    action: str
    rationale: str

    @field_validator("action", "rationale")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "recommendation field")


class Reasoning(BaseModel):
    """Reviewer-visible reasoning for a generated artifact."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    evidence: list[str] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def summary_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "reasoning summary")


class ProductIdea(BaseModel):
    """User-provided product idea input."""

    model_config = ConfigDict(extra="forbid")

    raw_text: str
    title: str | None = None
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    context_notes: list[str] = Field(default_factory=list)

    @field_validator("raw_text")
    @classmethod
    def raw_text_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "product idea")


RequirementCategory = Literal["functional", "non-functional"]


class ProductRequirement(BaseModel):
    """A product requirement produced by the Product Manager workflow."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    category: RequirementCategory | None = None
    reasoning: str | None = None

    @field_validator("id", "text")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "requirement field")


class AcceptanceCriterion(BaseModel):
    """Given/when/then acceptance criterion for a user story."""

    model_config = ConfigDict(extra="forbid")

    given: str
    when: str
    then: str

    @field_validator("given", "when", "then")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "acceptance criterion field")


class UserStory(BaseModel):
    """SprintPilot Core v1 Agile user story."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    priority: str
    actor: str
    goal: str
    benefit: str
    acceptance_criteria: list[AcceptanceCriterion]

    @field_validator("id", "title", "priority", "actor", "goal", "benefit")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "user story field")

    @field_validator("acceptance_criteria")
    @classmethod
    def acceptance_criteria_must_not_be_empty(
        cls, value: list[AcceptanceCriterion]
    ) -> list[AcceptanceCriterion]:
        if not value:
            raise ValueError("user story must include acceptance criteria")
        return value


class ProductDefinition(BaseModel):
    """Structured product definition output for User Story 1."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    primary_users: list[str]
    functional_requirements: list[ProductRequirement]
    non_functional_requirements: list[ProductRequirement] = Field(default_factory=list)
    user_stories: list[UserStory]
    assumptions: list[Assumption] = Field(default_factory=list)
    missing_information: list[MissingInformation] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    reasoning: Reasoning
    review_required: bool = True

    @field_validator("summary")
    @classmethod
    def summary_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "product definition summary")

    @field_validator("primary_users")
    @classmethod
    def primary_users_must_not_be_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("product definition must include primary users")
        return [_strip_required(user, "primary user") for user in value]

    @model_validator(mode="after")
    def required_sections_must_be_present(self) -> "ProductDefinition":
        if not self.functional_requirements:
            raise ValueError("product definition must include functional requirements")
        if not self.user_stories:
            raise ValueError("product definition must include user stories")
        return self


class StackCategory(BaseModel):
    """A recommended technology stack category without provider-specific implementation."""

    model_config = ConfigDict(extra="forbid")

    name: str
    recommendation: str
    rationale: str

    @field_validator("name", "recommendation", "rationale")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "stack category field")


class SystemComponent(BaseModel):
    """High-level architecture component and responsibility."""

    model_config = ConfigDict(extra="forbid")

    name: str
    responsibility: str
    interactions: list[str] = Field(default_factory=list)

    @field_validator("name", "responsibility")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "system component field")


class ArchitectureTradeoff(BaseModel):
    """Architecture decision tradeoff for human review."""

    model_config = ConfigDict(extra="forbid")

    decision: str
    benefit: str
    cost: str

    @field_validator("decision", "benefit", "cost")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "architecture tradeoff field")


class ArchitecturePlan(BaseModel):
    """Structured architecture guidance output for User Story 2."""

    model_config = ConfigDict(extra="forbid")

    recommended_architecture: str
    technology_stack_categories: list[StackCategory]
    system_components: list[SystemComponent]
    database_considerations: str | None = None
    tradeoffs: list[ArchitectureTradeoff] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    open_questions: list[MissingInformation] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    reasoning: Reasoning
    review_required: bool = True

    @field_validator("recommended_architecture")
    @classmethod
    def architecture_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "recommended architecture")

    @field_validator("technology_stack_categories")
    @classmethod
    def stack_categories_must_not_be_empty(cls, value: list[StackCategory]) -> list[StackCategory]:
        if not value:
            raise ValueError("architecture plan must include technology stack categories")
        return value

    @field_validator("system_components")
    @classmethod
    def system_components_must_not_be_empty(cls, value: list[SystemComponent]) -> list[SystemComponent]:
        if not value:
            raise ValueError("architecture plan must include system components")
        return value


class Epic(BaseModel):
    """Agile epic in a SprintPilot sprint plan."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    objective: str

    @field_validator("id", "title", "objective")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "epic field")


class SprintStory(BaseModel):
    """Sprint-ready story for engineering handoff."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    priority: str
    acceptance_criteria: list[str]

    @field_validator("id", "title", "priority")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "sprint story field")

    @field_validator("acceptance_criteria")
    @classmethod
    def acceptance_criteria_must_not_be_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("sprint story must include acceptance criteria")
        return [_strip_required(item, "sprint story acceptance criterion") for item in value]


class StoryTask(BaseModel):
    """Task belonging to a sprint-ready story."""

    model_config = ConfigDict(extra="forbid")

    id: str
    story_id: str
    description: str

    @field_validator("id", "story_id", "description")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "story task field")


class StoryPointEstimate(BaseModel):
    """Story point estimate with reviewer-visible reasoning."""

    model_config = ConfigDict(extra="forbid")

    story_id: str
    points: int = Field(ge=1)
    reasoning: str

    @field_validator("story_id", "reasoning")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "story point estimate field")


class PlanningDependency(BaseModel):
    """Dependency or sequencing constraint in a sprint plan."""

    model_config = ConfigDict(extra="forbid")

    description: str
    impacts: list[str] = Field(default_factory=list)

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, value: str) -> str:
        return _strip_required(value, "planning dependency description")


class SprintPlan(BaseModel):
    """Structured sprint planning output for User Story 3."""

    model_config = ConfigDict(extra="forbid")

    epics: list[Epic]
    stories: list[SprintStory]
    tasks: list[StoryTask]
    story_point_estimates: list[StoryPointEstimate]
    dependencies: list[PlanningDependency] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    reasoning: Reasoning
    review_required: bool = True

    @model_validator(mode="after")
    def required_agile_sections_must_be_present(self) -> "SprintPlan":
        if not self.epics:
            raise ValueError("sprint plan must include epics")
        if not self.stories:
            raise ValueError("sprint plan must include stories")
        if not self.tasks:
            raise ValueError("sprint plan must include tasks")
        if not self.story_point_estimates:
            raise ValueError("sprint plan must include story point estimates")
        return self
