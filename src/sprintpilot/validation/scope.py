"""Core v1 scope validation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ForbiddenScopeFinding:
    """A detected out-of-scope Core v1 capability."""

    label: str
    matched_text: str
    field_path: str | None = None


_FORBIDDEN_SCOPE_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("GitHub integration", ("github", "pull request", "repository automation")),
    ("Taiga integration", ("taiga",)),
    ("code generation", ("code generation", "generate source code", "source code generation")),
    (
        "analytics",
        (
            "sprintpilot analytics",
            "analytics module",
            "analytics subsystem",
            "analytics platform",
            "analytics dashboard",
            "standalone analytics",
            "standalone analytics module",
            "standalone analytics dashboard",
            "metrics dashboard",
            "reporting platform",
            "reporting system",
            "analytics reporting",
        ),
    ),
    ("cloud collaboration", ("cloud collaboration", "collaboration service")),
    ("review agents", ("review agent", "review agents")),
    ("RAG", ("rag", "retrieval augmented generation")),
    ("deployment concerns", ("deployment", "deploy", "production hosting")),
    ("CI/CD", ("ci/cd", "continuous integration", "continuous deployment")),
    (
        "multi-user collaboration",
        (
            "multi-user",
            "multi user",
            "team collaboration",
            "shared workspace",
            "shared workspaces",
            "team account",
            "team accounts",
            "commenting",
            "comment on applications",
            "comments on applications",
            "advisor comments",
            "advisor commenting",
            "co-edit",
            "co-editing",
            "coediting",
            "sharing workflow",
            "sharing workflows",
            "share applications",
            "shared applications",
            "advisor collaboration",
            "group collaboration",
            "role-based teamwork",
            "role based teamwork",
            "teamwork features",
            "collaboration features",
            "collaboration workflows",
        ),
    ),
)


def detect_forbidden_scope(text: str) -> list[ForbiddenScopeFinding]:
    """Return Core v1 forbidden capabilities found in text."""

    return _detect_scope_terms(text, _FORBIDDEN_SCOPE_TERMS)


def detect_forbidden_scope_in_value(value: object) -> list[ForbiddenScopeFinding]:
    """Return Core v1 forbidden capabilities found in structured text values."""

    findings: list[ForbiddenScopeFinding] = []
    seen_labels: set[str] = set()
    for path, text in _iter_text_values(value):
        for finding in _detect_scope_terms(text, _FORBIDDEN_SCOPE_TERMS, field_path=path):
            if finding.label in seen_labels:
                continue
            seen_labels.add(finding.label)
            findings.append(finding)
    return findings


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
    *,
    field_path: str | None = None,
) -> list[ForbiddenScopeFinding]:
    findings: list[ForbiddenScopeFinding] = []
    for label, terms in terms_by_label:
        for term in terms:
            matched_text = _matched_scope_text(text, term)
            if matched_text is not None:
                findings.append(
                    ForbiddenScopeFinding(
                        label=label,
                        matched_text=matched_text,
                        field_path=field_path,
                    )
                )
                break
    return findings


def has_forbidden_scope(text: str) -> bool:
    """Return whether text includes a Core v1 forbidden capability."""

    return bool(detect_forbidden_scope(text))


def _matches_scope_term(normalized_text: str, term: str) -> bool:
    return _matched_scope_text(normalized_text, term) is not None


def _matched_scope_text(text: str, term: str) -> str | None:
    escaped = re.escape(term)
    match = re.search(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", text, flags=re.IGNORECASE)
    return match.group(0) if match else None


def _iter_text_values(value: object, path: str | None = None) -> list[tuple[str | None, str]]:
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, list):
        findings: list[tuple[str | None, str]] = []
        for index, item in enumerate(value):
            item_path = f"{path}[{index}]" if path else f"[{index}]"
            findings.extend(_iter_text_values(item, item_path))
        return findings
    if isinstance(value, dict):
        findings = []
        for key, item in value.items():
            item_path = f"{path}.{key}" if path else str(key)
            findings.extend(_iter_text_values(item, item_path))
        return findings
    return []


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
