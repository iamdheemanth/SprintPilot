"""Markdown report assembly and rendering for SprintPilot Core v1."""

from __future__ import annotations

import re
from pathlib import Path

from sprintpilot.domain import (
    ArchitecturePlan,
    CORE_V1_EXCLUDED_CAPABILITIES,
    CORE_V1_INCLUDED_CAPABILITIES,
    EngineeringConfidenceAssessment,
    ProductDefinition,
    ProductIdea,
    SprintPilotReport,
    SprintPlan,
)


class ReportWriteError(RuntimeError):
    """Raised when a report cannot be written to the requested path."""


_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b[A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD)\s*=", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
)

_DEDUPLICATION_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)


def assemble_report(
    *,
    title: str,
    product_idea: ProductIdea,
    product_definition: ProductDefinition,
    architecture_plan: ArchitecturePlan,
    sprint_plan: SprintPlan,
    confidence_assessment: EngineeringConfidenceAssessment,
) -> SprintPilotReport:
    """Assemble the final Core v1 report from already-validated artifacts."""

    return SprintPilotReport(
        title=title,
        product_idea=product_idea,
        product_definition=product_definition,
        architecture_plan=architecture_plan,
        sprint_plan=sprint_plan,
        confidence_assessment=confidence_assessment,
    )


def render_markdown_report(report: SprintPilotReport) -> str:
    """Render a Core v1 report as human-reviewable Markdown."""

    lines: list[str] = [
        f"# SprintPilot Report: {report.title}",
        "",
        "_SprintPilot generated artifacts require human review before implementation._",
        "",
        "## Original Product Idea",
        "",
        report.product_idea.raw_text,
        "",
        "## Product Definition",
        "",
        f"**Summary:** {report.product_definition.summary}",
        "",
        "**Primary users:**",
        *_bullets(report.product_definition.primary_users),
        "",
        "**Functional requirements:**",
        *_bullets(
            f"{item.id}: {item.text}"
            for item in report.product_definition.functional_requirements
        ),
        "",
        "**Non-functional requirements:**",
        *_bullets(
            f"{item.id}: {item.text}"
            for item in report.product_definition.non_functional_requirements
        ),
        "",
        "**User stories:**",
        *_product_story_lines(report.product_definition),
        "",
        "**Assumptions:**",
        *_bullets(item.text for item in report.product_definition.assumptions),
        "",
        "**Reasoning:**",
        report.product_definition.reasoning.summary,
        "",
        "## Architecture Plan",
        "",
        f"**Recommended architecture:** {report.architecture_plan.recommended_architecture}",
        "",
        "**Technology stack categories:**",
        *_bullets(
            f"{item.name}: {item.recommendation} - {item.rationale}"
            for item in report.architecture_plan.technology_stack_categories
        ),
        "",
        "**System components:**",
        *_bullets(
            f"{item.name}: {item.responsibility}"
            for item in report.architecture_plan.system_components
        ),
        "",
        f"**Database considerations:** {report.architecture_plan.database_considerations or 'None identified for Core v1.'}",
        "",
        "**Tradeoffs:**",
        *_bullets(
            f"{item.decision}: benefit - {item.benefit}; cost - {item.cost}"
            for item in report.architecture_plan.tradeoffs
        ),
        "",
        "**Assumptions:**",
        *_bullets(item.text for item in report.architecture_plan.assumptions),
        "",
        "**Open questions:**",
        *_bullets(
            f"{item.question} Impact: {item.impact}"
            for item in report.architecture_plan.open_questions
        ),
        "",
        "**Reasoning:**",
        report.architecture_plan.reasoning.summary,
        "",
        "## Sprint Plan",
        "",
        "**Epics:**",
        *_bullets(f"{item.id}: {item.title} - {item.objective}" for item in report.sprint_plan.epics),
        "",
        "**Sprint-ready stories:**",
        *_bullets(f"{item.id}: {item.title} ({item.priority})" for item in report.sprint_plan.stories),
        "",
        "**Tasks:**",
        *_bullets(
            f"{item.id}: {item.description} [{item.story_id}]"
            for item in report.sprint_plan.tasks
        ),
        "",
        "**Dependencies:**",
        *_bullets(item.description for item in report.sprint_plan.dependencies),
        "",
        "**Story point estimates:**",
        *_bullets(
            f"{item.story_id}: {item.points} points - {item.reasoning}"
            for item in report.sprint_plan.story_point_estimates
        ),
        "",
        "**Estimate reasoning:**",
        report.sprint_plan.reasoning.summary,
        "",
        "## Engineering Confidence Assessment",
        "",
        f"**Overall score:** {report.confidence_assessment.overall_score}/100",
        "",
        "**Factor scores:**",
        *_bullets(
            f"{item.label}: {item.score}/100 (weight {item.weight}) - {item.reasoning}"
            for item in report.confidence_assessment.factor_scores
        ),
        "",
        "**Score caps and warnings:**",
        *_bullets(
            f"{item.reason}: capped at {item.cap} - {item.explanation}"
            for item in report.confidence_assessment.score_caps
        ),
        "",
        "**Reasoning:**",
        report.confidence_assessment.reasoning.summary,
        "",
        "## Risks",
        "",
        *_risk_lines(report),
        "",
        "## Missing Information",
        "",
        *_missing_information_lines(report),
        "",
        "## Recommended Actions",
        "",
        *_recommendation_lines(report),
        "",
        "## Scope Boundaries",
        "",
        "**Included in Core v1:**",
        *_bullets(report.included_capabilities or CORE_V1_INCLUDED_CAPABILITIES),
        "",
        "**Excluded from Core v1:**",
        *_bullets(report.excluded_capabilities or CORE_V1_EXCLUDED_CAPABILITIES),
        "",
    ]
    return "\n".join(lines)


def validate_report_scope_boundaries(markdown: str) -> list[str]:
    """Validate report text for local-report safety and scope-boundary expectations."""

    errors: list[str] = []
    for pattern in _SECRET_PATTERNS:
        if pattern.search(markdown):
            errors.append("Report content appears to contain a secret or credential.")
            break
    return errors


def safe_report_filename(title: str) -> str:
    """Return a filesystem-safe Markdown filename for a report title."""

    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", title.strip().lower()).strip("-._")
    if not normalized:
        normalized = "sprintpilot-report"
    return f"{normalized[:80]}.md"


def write_markdown_report(report: SprintPilotReport, output: str | Path | None = None) -> Path:
    """Write a Markdown report to a file or directory and return the report path."""

    markdown = render_markdown_report(report)
    validation_errors = validate_report_scope_boundaries(markdown)
    if validation_errors:
        raise ReportWriteError("; ".join(validation_errors))

    target = Path(output) if output is not None else Path.cwd()
    report_path = target if target.suffix.lower() == ".md" else target / safe_report_filename(report.title)

    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        raise ReportWriteError(f"Unable to write report to {report_path}") from exc
    return report_path


def _bullets(items) -> list[str]:
    values = [str(item) for item in items if str(item).strip()]
    if not values:
        return ["- None identified."]
    return [f"- {item}" for item in values]


def _deduplicated_normalized(items) -> list[str]:
    """Return first-seen items after normalized text comparison."""

    deduplicated: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item).strip()
        if not value:
            continue
        normalized = _normalize_for_deduplication(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduplicated.append(value)
    return deduplicated


def _normalize_for_deduplication(value: str) -> str:
    without_punctuation = _DEDUPLICATION_PUNCTUATION.sub(" ", value.casefold())
    return " ".join(without_punctuation.split())


def _product_story_lines(product_definition: ProductDefinition) -> list[str]:
    lines: list[str] = []
    for story in product_definition.user_stories:
        lines.append(f"- {story.id}: As a {story.actor}, I want to {story.goal}, so that {story.benefit}.")
        for criterion in story.acceptance_criteria:
            lines.append(
                f"  - Given {criterion.given}, when {criterion.when}, then {criterion.then}."
            )
    return lines or ["- None identified."]


def _risk_lines(report: SprintPilotReport) -> list[str]:
    risks = [
        *report.product_definition.risks,
        *report.architecture_plan.risks,
        *report.sprint_plan.risks,
        *report.confidence_assessment.risks,
    ]
    return _bullets(
        _deduplicated_normalized(
            f"{risk.description}"
            + (f" Impact: {risk.impact}" if risk.impact else "")
            + (f" Mitigation: {risk.mitigation}" if risk.mitigation else "")
            for risk in risks
        )
    )


def _missing_information_lines(report: SprintPilotReport) -> list[str]:
    missing = [
        *report.product_definition.missing_information,
        *report.architecture_plan.open_questions,
        *report.confidence_assessment.missing_information,
    ]
    return _bullets(
        _deduplicated_normalized(
            f"{item.question} Impact: {item.impact}" for item in missing
        )
    )


def _recommendation_lines(report: SprintPilotReport) -> list[str]:
    recommendations = [
        *report.product_definition.recommendations,
        *report.confidence_assessment.recommendations,
    ]
    return _bullets(
        _deduplicated_normalized(
            f"{item.action} Rationale: {item.rationale}" for item in recommendations
        )
    )
