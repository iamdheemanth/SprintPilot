"""Core v1 scope validation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ForbiddenScopeFinding:
    """A detected out-of-scope Core v1 capability."""

    label: str
    matched_text: str


_FORBIDDEN_SCOPE_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("GitHub integration", ("github", "pull request", "repository automation")),
    ("Taiga integration", ("taiga",)),
    ("code generation", ("code generation", "generate source code", "source code generation")),
    ("analytics", ("sprintpilot analytics", "analytics module", "metrics dashboard")),
    ("cloud collaboration", ("cloud collaboration", "collaboration service")),
    ("review agents", ("review agent", "review agents")),
    ("RAG", ("rag", "retrieval augmented generation")),
    ("deployment concerns", ("deployment", "deploy", "production hosting")),
    ("CI/CD", ("ci/cd", "continuous integration", "continuous deployment")),
    ("multi-user collaboration", ("multi-user", "multi user", "team collaboration")),
)


def detect_forbidden_scope(text: str) -> list[ForbiddenScopeFinding]:
    """Return Core v1 forbidden capabilities found in text."""

    return _detect_scope_terms(text, _FORBIDDEN_SCOPE_TERMS)


def detect_architecture_forbidden_scope(text: str) -> list[ForbiddenScopeFinding]:
    """Return architecture-stage forbidden capabilities found in generated architecture text."""

    findings = [
        *_detect_scope_terms(text, _FORBIDDEN_SCOPE_TERMS),
        *_detect_scope_terms(text, _ARCHITECTURE_FORBIDDEN_SCOPE_TERMS),
    ]
    unique_findings: list[ForbiddenScopeFinding] = []
    seen_labels: set[str] = set()
    for finding in findings:
        if finding.label in seen_labels:
            continue
        seen_labels.add(finding.label)
        unique_findings.append(finding)
    return unique_findings


def _detect_scope_terms(
    text: str,
    terms_by_label: tuple[tuple[str, tuple[str, ...]], ...],
) -> list[ForbiddenScopeFinding]:
    normalized = text.lower()
    findings: list[ForbiddenScopeFinding] = []
    for label, terms in terms_by_label:
        for term in terms:
            if _matches_scope_term(normalized, term):
                findings.append(ForbiddenScopeFinding(label=label, matched_text=term))
                break
    return findings


def has_forbidden_scope(text: str) -> bool:
    """Return whether text includes a Core v1 forbidden capability."""

    return bool(detect_forbidden_scope(text))


def _matches_scope_term(normalized_text: str, term: str) -> bool:
    escaped = re.escape(term.lower())
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", normalized_text) is not None


_ARCHITECTURE_FORBIDDEN_SCOPE_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "analytics",
        (
            "analytics",
            "application analytics",
            "metrics",
            "metric",
            "dashboard analytics",
            "conversion rate",
            "conversion rates",
            "insights",
            "aggregation",
            "aggregations",
        ),
    ),
    (
        "deployment concerns",
        (
            "deployment",
            "deploy",
            "production hosting",
            "hosting",
            "release engineering",
            "operational",
            "operations",
        ),
    ),
    ("CI/CD", ("ci/cd", "continuous integration", "continuous deployment")),
    ("cloud hosting", ("cloud hosting", "cloud deployment")),
    ("observability dashboards", ("observability", "observability dashboard", "monitoring dashboard")),
    ("multi-user collaboration", ("multi-user", "multi user", "team collaboration", "collaboration")),
)
