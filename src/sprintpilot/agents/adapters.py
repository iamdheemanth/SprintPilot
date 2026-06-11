"""Adapters from provider-neutral LLM output to SprintPilot domain models."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import ValidationError

from sprintpilot.domain import ArchitecturePlan, ProductDefinition, SprintPlan
from sprintpilot.llm import StructuredGenerationResult
from sprintpilot.validation.scope import detect_architecture_forbidden_scope, detect_forbidden_scope

T = TypeVar("T")


class ParsedArtifact(Generic[T]):
    """Parsed domain artifact with validation errors when parsing fails."""

    def __init__(self, value: T | None, validation_errors: list[str] | None = None) -> None:
        self.value = value
        self.validation_errors = validation_errors or []

    @property
    def is_valid(self) -> bool:
        return self.value is not None and not self.validation_errors

    def __getattr__(self, name: str) -> object:
        if self.value is None:
            raise AttributeError(name)
        return getattr(self.value, name)


def parse_product_definition_result(
    result: StructuredGenerationResult,
) -> ParsedArtifact[ProductDefinition]:
    """Parse structured LLM output into a ProductDefinition."""

    if not result.is_valid:
        return ParsedArtifact(None, result.validation_errors)

    try:
        definition = ProductDefinition.model_validate(result.data)
    except ValidationError as exc:
        return ParsedArtifact(None, [str(error["msg"]) for error in exc.errors()])

    findings = detect_forbidden_scope(definition.model_dump_json())
    if findings:
        labels = ", ".join(finding.label for finding in findings)
        return ParsedArtifact(None, [f"Product definition includes out-of-scope content: {labels}"])

    return ParsedArtifact(definition)


def parse_architecture_plan_result(
    result: StructuredGenerationResult,
) -> ParsedArtifact[ArchitecturePlan]:
    """Parse structured LLM output into an ArchitecturePlan."""

    if not result.is_valid:
        return ParsedArtifact(None, result.validation_errors)

    try:
        plan = ArchitecturePlan.model_validate(result.data)
    except ValidationError as exc:
        return ParsedArtifact(None, [str(error["msg"]) for error in exc.errors()])

    findings = detect_architecture_forbidden_scope(plan.model_dump_json())
    if findings:
        labels = ", ".join(finding.label for finding in findings)
        return ParsedArtifact(None, [f"Architecture plan includes out-of-scope content: {labels}"])

    return ParsedArtifact(plan)


def parse_sprint_plan_result(
    result: StructuredGenerationResult,
) -> ParsedArtifact[SprintPlan]:
    """Parse structured LLM output into a SprintPlan."""

    if not result.is_valid:
        return ParsedArtifact(None, result.validation_errors)

    try:
        plan = SprintPlan.model_validate(result.data)
    except ValidationError as exc:
        return ParsedArtifact(None, [str(error["msg"]) for error in exc.errors()])

    findings = detect_forbidden_scope(plan.model_dump_json())
    if findings:
        labels = ", ".join(finding.label for finding in findings)
        return ParsedArtifact(None, [f"Sprint plan includes out-of-scope content: {labels}"])

    return ParsedArtifact(plan)
