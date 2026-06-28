from __future__ import annotations

from sprintpilot.validation.scope import (
    detect_architecture_forbidden_scope,
    detect_forbidden_scope,
    has_forbidden_scope,
)


def test_detects_core_v1_forbidden_scope_terms() -> None:
    findings = detect_forbidden_scope(
        "Generate the plan, open GitHub pull requests, configure CI/CD deployment and add a SprintPilot analytics module."
    )

    labels = {finding.label for finding in findings}

    assert "GitHub integration" in labels
    assert "CI/CD" in labels
    assert "deployment concerns" in labels
    assert "analytics" in labels


def test_safe_product_definition_has_no_forbidden_scope() -> None:
    assert has_forbidden_scope("Create user stories and acceptance criteria with reasoning.") is False


def test_allows_target_product_application_analytics() -> None:
    assert (
        has_forbidden_scope(
            "The student internship tracker should include application analytics for students."
        )
        is False
    )


def test_allows_students_and_users_without_collaboration_features() -> None:
    text = (
        "Students can track applications, interview stages, offers, deadlines, "
        "recruiter contacts and their own application analytics."
    )

    assert has_forbidden_scope(text) is False


def test_allows_personal_student_application_metrics() -> None:
    text = (
        "The individual student can see total applications, applications by status, "
        "interview and offer counts, and an upcoming deadline summary for their own applications."
    )

    assert has_forbidden_scope(text) is False


def test_rejects_product_collaboration_features_precisely() -> None:
    findings = detect_forbidden_scope(
        "Students can invite advisors into shared workspaces, comment on applications, "
        "co-edit notes and manage team accounts with role-based teamwork features."
    )

    labels = {finding.label for finding in findings}

    assert labels == {"multi-user collaboration"}


def test_rejects_analytics_when_it_becomes_a_standalone_subsystem() -> None:
    findings = detect_forbidden_scope(
        "The product includes a separate analytics module, analytics dashboard, "
        "reporting platform and reporting system."
    )

    labels = {finding.label for finding in findings}

    assert labels == {"analytics"}


def test_architecture_scope_rejects_application_analytics_when_generated_in_architecture_plan() -> None:
    findings = detect_architecture_forbidden_scope(
        "The Backend API performs application analytics and displays conversion metrics."
    )

    assert [finding.label for finding in findings] == ["analytics"]


def test_rag_scope_term_must_match_as_a_word() -> None:
    assert has_forbidden_scope("Support drag-and-drop ordering of applications.") is False
