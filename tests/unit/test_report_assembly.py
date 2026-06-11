from __future__ import annotations

from tests.unit.test_architect_adapter import _valid_architecture_payload
from tests.unit.test_architect_prompts import _definition
from tests.unit.test_scrum_master_adapter import _valid_sprint_payload

from sprintpilot.domain import (
    ArchitecturePlan,
    MissingInformation,
    ProductIdea,
    Recommendation,
    Risk,
    SprintPilotReport,
    SprintPlan,
)
from sprintpilot.scoring import assess_engineering_confidence
from sprintpilot.reporting import render_markdown_report


def _report() -> SprintPilotReport:
    product_definition = _definition()
    architecture_plan = ArchitecturePlan.model_validate(_valid_architecture_payload())
    sprint_plan = SprintPlan.model_validate(_valid_sprint_payload())
    confidence = assess_engineering_confidence(
        product_definition=product_definition,
        architecture_plan=architecture_plan,
        sprint_plan=sprint_plan,
    )
    return SprintPilotReport(
        title="Internship Tracker",
        product_idea=ProductIdea(raw_text="Build a student internship tracking platform."),
        product_definition=product_definition,
        architecture_plan=architecture_plan,
        sprint_plan=sprint_plan,
        confidence_assessment=confidence,
    )


def test_markdown_report_preserves_required_schema_sections() -> None:
    markdown = render_markdown_report(_report())

    required_headings = [
        "# SprintPilot Report: Internship Tracker",
        "## Original Product Idea",
        "## Product Definition",
        "## Architecture Plan",
        "## Sprint Plan",
        "## Engineering Confidence Assessment",
        "## Risks",
        "## Missing Information",
        "## Recommended Actions",
        "## Scope Boundaries",
    ]
    for heading in required_headings:
        assert heading in markdown


def test_markdown_report_includes_reasoning_and_confidence_factors() -> None:
    markdown = render_markdown_report(_report())

    assert "Requirement clarity" in markdown
    assert "Architecture completeness" in markdown
    assert "Stories are ordered by Core v1 workflow value." in markdown
    assert "generated artifacts require human review" in markdown.lower()


def test_markdown_report_deduplicates_risks_and_preserves_order() -> None:
    report = _report()
    first_risk = Risk(
        description="Acceptance criteria may be incomplete.",
        impact="Delivery readiness is reduced.",
        mitigation="Review each story before sprint commitment.",
    )
    duplicate_risk = Risk(
        description="acceptance criteria may be incomplete",
        impact="Delivery readiness is reduced",
        mitigation="Review each story before sprint commitment",
    )
    distinct_risk = Risk(
        description="Provider responses may omit edge cases.",
        impact="Planning gaps may remain.",
    )
    report.product_definition.risks[:] = [first_risk]
    report.architecture_plan.risks[:] = [duplicate_risk]
    report.sprint_plan.risks[:] = [distinct_risk]

    markdown = render_markdown_report(report)

    assert markdown.count("Acceptance criteria may be incomplete.") == 1
    assert "acceptance criteria may be incomplete" not in markdown
    assert markdown.index("Acceptance criteria may be incomplete.") < markdown.index(
        "Provider responses may omit edge cases."
    )


def test_markdown_report_deduplicates_missing_information_and_keeps_distinct_items() -> None:
    report = _report()
    first_missing = MissingInformation(
        question="Who approves final sprint scope?",
        impact="Defines the human review gate.",
    )
    duplicate_missing = MissingInformation(
        question="who approves final sprint scope",
        impact="Defines the human review gate",
    )
    distinct_missing = MissingInformation(
        question="Which reporting format is preferred?",
        impact="Affects handoff readability.",
    )
    report.product_definition.missing_information[:] = [first_missing]
    report.architecture_plan.open_questions[:] = [duplicate_missing]
    report.confidence_assessment.missing_information[:] = [distinct_missing]

    markdown = render_markdown_report(report)
    missing_information_section = _section(
        markdown, "## Missing Information", "## Recommended Actions"
    )

    assert missing_information_section.count("Who approves final sprint scope?") == 1
    assert "who approves final sprint scope" not in missing_information_section
    assert "Which reporting format is preferred?" in missing_information_section
    assert missing_information_section.index(
        "Who approves final sprint scope?"
    ) < missing_information_section.index(
        "Which reporting format is preferred?"
    )


def test_markdown_report_deduplicates_recommendations_when_rendering() -> None:
    report = _report()
    first_recommendation = Recommendation(
        action="Clarify release-blocking decisions.",
        rationale="Readiness depends on unresolved scope choices.",
    )
    duplicate_recommendation = Recommendation(
        action="clarify release blocking decisions",
        rationale="Readiness depends on unresolved scope choices",
    )
    report.product_definition.recommendations[:] = [first_recommendation]
    report.confidence_assessment.recommendations[:] = [duplicate_recommendation]

    markdown = render_markdown_report(report)

    assert markdown.count("Clarify release-blocking decisions.") == 1
    assert "clarify release blocking decisions" not in markdown


def _section(markdown: str, start_heading: str, end_heading: str) -> str:
    start = markdown.index(start_heading)
    end = markdown.index(end_heading, start)
    return markdown[start:end]
