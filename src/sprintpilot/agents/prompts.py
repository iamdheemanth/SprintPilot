"""Prompt construction for SprintPilot Core v1 agents."""

from __future__ import annotations

import re

from sprintpilot.domain import ArchitecturePlan, ProductDefinition, ProductIdea
from sprintpilot.llm import Message


def build_product_manager_messages(product_idea: ProductIdea) -> list[Message]:
    """Build provider-neutral messages for the Product Manager workflow."""

    system_prompt = (
        "You are the SprintPilot Product Manager Agent. Generate only SprintPilot Core v1 "
        "product definition artifacts: product summary, functional requirements, "
        "non-functional requirements, user stories, acceptance criteria, assumptions, "
        "missing information and reasoning. Core v1 product definitions are a "
        "single-student product for one individual student user using their own local "
        "planning and tracking workflow. "
        "Multiple students may be described as the target audience only as separate end "
        "users, not collaboration between users. Do not generate source code, "
        "architecture plans, sprint plans, confidence scores, GitHub or Taiga "
        "integration, analytics modules, cloud collaboration, review agents, RAG, "
        "deployment, CI/CD or multi-user collaboration. Explicitly exclude shared "
        "workspaces, team accounts, commenting, co-editing, sharing workflows, advisor "
        "or group collaboration, and role-based teamwork features. Application analytics "
        "are allowed only when they mean the student's own application tracking insights: "
        "personal insights for the individual student's own applications, such as total "
        "applications, applications by status, interview/offer counts, and an upcoming "
        "deadline summary. Explicitly exclude "
        "analytics as a standalone module, platform, dashboard, or reporting system. "
        "Return structured data matching the ProductDefinition contract."
    )
    user_prompt = f"Product idea:\n{product_idea.raw_text}"
    return [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt),
    ]


def build_product_manager_repair_messages(
    *,
    product_definition: ProductDefinition,
    validation_errors: list[str],
) -> list[Message]:
    """Build a corrective ProductDefinition prompt after scope validation rejects output."""

    system_prompt = (
        "You are the SprintPilot Product Manager Repair Agent. Repair the generated "
        "ProductDefinition for SprintPilot Core v1. This is a maximum one repair pass. "
        "Remove collaboration features, shared workspaces, team accounts, advisor or "
        "team collaboration, co-editing, sharing workflows, and role-based teamwork. "
        "Convert collaboration-oriented requirements into single-user equivalents when "
        "possible. Preserve requirements, user stories, acceptance criteria, assumptions, "
        "missing information, reasoning, and personal application analytics. Preserve "
        "personal application analytics only as the individual student's own summary "
        "metrics, such as total applications, applications by status, interview/offer "
        "counts, and upcoming deadline summary. Do not create analytics modules, "
        "analytics dashboards, analytics platforms, reporting systems, architecture, "
        "sprint plans, confidence scores, integrations, or code. Return structured data "
        "matching the ProductDefinition contract."
    )
    user_prompt = (
        "The previous ProductDefinition was rejected for Core v1 scope violations:\n"
        f"{'; '.join(validation_errors)}\n\n"
        "Repair this ProductDefinition JSON while preserving valid planning content:\n"
        f"{product_definition.model_dump_json(indent=2)}"
    )
    return [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt),
    ]


def build_architect_messages(product_definition: ProductDefinition) -> list[Message]:
    """Build provider-neutral messages for the Architect workflow."""

    system_prompt = (
        "You are the SprintPilot Architect Agent. For SprintPilot Core v1, only produce "
        "recommended architecture, high-level system components, technology stack "
        "categories, database considerations, architecture tradeoffs, assumptions, "
        "open questions, risks and reasoning. The architecture stage must only produce system "
        "components, stack categories, database considerations, architecture tradeoffs, "
        "assumptions, open questions, risks and reasoning beyond the concise "
        "recommended architecture summary. Keep "
        "recommendations advisory and explain tradeoffs. Do not introduce analytics "
        "modules, deployment concerns, CI/CD, cloud hosting, release engineering, "
        "observability dashboards, GitHub or Taiga integration, cloud collaboration, "
        "review agents, RAG, multi-user collaboration, source code, sprint plans, "
        "confidence scores or reports. If the product definition mentions application "
        "analytics, treat it as a product concept only; do not expand it into "
        "architecture scope for Core v1. Do not mention analytics in the ArchitecturePlan. "
        "Do not mention deployment, hosting, observability, operations, production, "
        "or release engineering in the ArchitecturePlan. Do not mention multi-user "
        "collaboration in the ArchitecturePlan, even to say it is excluded. "
        "Return structured data matching the ArchitecturePlan contract. Do not generate source code."
    )
    architecture_requirements: list[str] = []
    excluded_requirements: list[str] = []
    for requirement in product_definition.functional_requirements:
        line = f"- {requirement.id}: {requirement.text}"
        if _is_architecture_excluded_requirement(requirement.text):
            excluded_requirements.append(
                f"- {requirement.id}: Product-level analytics concept omitted from architecture scope."
            )
        else:
            architecture_requirements.append(line)

    user_prompt = (
        "Product definition summary:\n"
        f"{_architecture_safe_summary(product_definition.summary)}\n\n"
        "Functional requirements for Core v1 architecture planning:\n"
        + "\n".join(architecture_requirements or ["- None after Core v1 architecture exclusions."])
    )
    if excluded_requirements:
        user_prompt += (
            "\n\nIntentionally excluded from Core v1 architecture scope:\n"
            + "\n".join(excluded_requirements)
            + "\nDo not create architecture components, stack recommendations, database design, "
            "risks, tradeoffs or reasoning for these excluded product concepts."
        )
    user_prompt += (
        "\n\nArchitecture output must stay local planning-only and omit analytics, "
        "deployment, hosting, observability, operations, production, release engineering, "
        "CI/CD and multi-user collaboration language."
    )
    return [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt),
    ]


def build_architect_retry_messages(
    product_definition: ProductDefinition,
    validation_errors: list[str],
) -> list[Message]:
    """Build a corrective architecture prompt after scope validation rejects output."""

    messages = build_architect_messages(product_definition)
    correction = (
        "The previous architecture output was rejected for Core v1 scope violations: "
        f"{'; '.join(validation_errors)}. Remove analytics, deployment, hosting, "
        "observability, operations, production, release engineering, CI/CD and "
        "multi-user collaboration language from every ArchitecturePlan field. Generate "
        "a fresh ArchitecturePlan using only local planning boundaries."
    )
    return [*messages, Message(role="user", content=correction)]


def build_scrum_master_messages(
    *,
    product_definition: ProductDefinition,
    architecture_plan: ArchitecturePlan,
) -> list[Message]:
    """Build provider-neutral messages for the Scrum Master workflow."""

    system_prompt = (
        "You are the SprintPilot Scrum Master Agent. Generate only SprintPilot Core v1 "
        "sprint planning artifacts: epics, sprint-ready stories, task breakdown, story "
        "point estimates, dependencies, sprint-specific assumptions, risks and estimate "
        "reasoning. Use standard Agile terminology and keep every estimate explainable. "
        "Do not generate source code, confidence scores, reports, GitHub or Taiga "
        "integration, analytics, cloud collaboration, review agents, RAG, deployment, "
        "CI/CD or multi-user collaboration. Return structured data matching the "
        "SprintPlan contract."
    )
    user_prompt = (
        "Product definition summary:\n"
        f"{product_definition.summary}\n\n"
        "Architecture plan:\n"
        f"{architecture_plan.recommended_architecture}"
    )
    return [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt),
    ]


def _is_architecture_excluded_requirement(text: str) -> bool:
    normalized = text.lower()
    return any(
        term in normalized
        for term in (
            "analytics",
            "metric",
            "dashboard",
            "insight",
            "conversion rate",
        )
    )


def _architecture_safe_summary(summary: str) -> str:
    sanitized = summary
    sanitized = re.sub(
        r"\s+with\s+application analytics\s+for\s+([^.]+)",
        r" for \1",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(r"\s+with\s+[^.]*analytics[^.]*", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r",?\s+and\s+providing\s+[^.]*analytics[^.]*", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r",?\s+including\s+[^.]*analytics[^.]*", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r",?\s+and\s+[^.]*analytics[^.]*", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"\s{2,}", " ", sanitized).strip()
    if sanitized and sanitized[-1] not in ".!?":
        sanitized += "."
    return sanitized or "Product concept retained for Core v1 architecture planning."
