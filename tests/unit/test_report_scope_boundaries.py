from __future__ import annotations

from tests.unit.test_report_assembly import _report

from sprintpilot.reporting import render_markdown_report, validate_report_scope_boundaries


def test_report_scope_boundaries_list_core_v1_exclusions() -> None:
    markdown = render_markdown_report(_report())

    assert "GitHub integration" in markdown
    assert "Taiga integration" in markdown
    assert "Code generation or scaffolding" in markdown
    assert "RAG systems" in markdown


def test_report_scope_validation_rejects_secret_like_content() -> None:
    errors = validate_report_scope_boundaries("SPRINTPILOT_API_KEY=secret")

    assert errors
    assert "secret" in errors[0].lower()
