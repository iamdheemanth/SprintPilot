"""Product Manager orchestration boundary.

The implementation deliberately depends only on SprintPilot's LLM abstraction. CrewAI
can be introduced behind this boundary later without leaking provider SDKs upward.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from sprintpilot.agents.adapters import (
    ParsedArtifact,
    parse_architecture_plan_result,
    parse_product_definition_result,
    parse_sprint_plan_result,
)
from sprintpilot.agents.prompts import (
    build_architect_messages,
    build_architect_retry_messages,
    build_product_manager_messages,
    build_scrum_master_messages,
)
from sprintpilot.domain import ArchitecturePlan, ProductDefinition, ProductIdea, SprintPlan
from sprintpilot.llm import LLMProvider, LLMRequest, StructuredGenerationResult
from sprintpilot.validation.scope import detect_architecture_forbidden_scope


class ProductManagerCrew:
    """Minimal Product Manager orchestration wrapper for Core v1."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def run(self, product_idea: ProductIdea) -> ParsedArtifact[ProductDefinition]:
        request = LLMRequest(
            messages=build_product_manager_messages(product_idea),
            response_schema={
                "name": "ProductDefinition",
                "schema": ProductDefinition.model_json_schema(),
            },
        )
        return parse_product_definition_result(self._provider.generate_structured(request))


def create_product_manager_crew(provider: LLMProvider) -> ProductManagerCrew:
    """Create Product Manager orchestration behind the LLM provider boundary."""

    return ProductManagerCrew(provider)


class ArchitectCrew:
    """Minimal Architect orchestration wrapper for Core v1."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def run(self, product_definition: ProductDefinition) -> ParsedArtifact[ArchitecturePlan]:
        request = LLMRequest(
            messages=build_architect_messages(product_definition),
            response_schema={
                "name": "ArchitecturePlan",
                "schema": ArchitecturePlan.model_json_schema(),
            },
        )
        parsed = parse_architecture_plan_result(self._provider.generate_structured(request))
        if parsed.is_valid:
            return parsed

        retry_request = LLMRequest(
            messages=build_architect_retry_messages(product_definition, parsed.validation_errors),
            response_schema={
                "name": "ArchitecturePlan",
                "schema": ArchitecturePlan.model_json_schema(),
            },
        )
        retry_result = self._provider.generate_structured(retry_request)
        retry_parsed = parse_architecture_plan_result(retry_result)
        if retry_parsed.is_valid:
            return retry_parsed
        if not _has_architecture_scope_error(retry_parsed.validation_errors):
            return retry_parsed

        sanitized_result = StructuredGenerationResult(
            data=_sanitize_architecture_payload(retry_result.data),
            raw_response=retry_result.raw_response,
        )
        return parse_architecture_plan_result(sanitized_result)


def create_architect_crew(provider: LLMProvider) -> ArchitectCrew:
    """Create Architect orchestration behind the LLM provider boundary."""

    return ArchitectCrew(provider)


class ScrumMasterCrew:
    """Minimal Scrum Master orchestration wrapper for Core v1."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def run(
        self,
        *,
        product_definition: ProductDefinition,
        architecture_plan: ArchitecturePlan,
    ) -> ParsedArtifact[SprintPlan]:
        request = LLMRequest(
            messages=build_scrum_master_messages(
                product_definition=product_definition,
                architecture_plan=architecture_plan,
            ),
            response_schema={
                "name": "SprintPlan",
                "schema": SprintPlan.model_json_schema(),
            },
        )
        return parse_sprint_plan_result(self._provider.generate_structured(request))


def create_scrum_master_crew(provider: LLMProvider) -> ScrumMasterCrew:
    """Create Scrum Master orchestration behind the LLM provider boundary."""

    return ScrumMasterCrew(provider)


def _has_architecture_scope_error(errors: list[str]) -> bool:
    return any("out-of-scope content" in error for error in errors)


def _sanitize_architecture_payload(data: Any) -> Any:
    if not isinstance(data, dict):
        return data

    payload = copy.deepcopy(data)
    payload["recommended_architecture"] = _sanitize_text(
        payload.get("recommended_architecture"),
        "A modular Core v1 architecture with separated interface, application, domain and data boundaries.",
    )
    payload["database_considerations"] = _sanitize_optional_text(
        payload.get("database_considerations"),
        "Data persistence considerations remain limited to Core v1 product data needs.",
    )
    payload["technology_stack_categories"] = [
        _sanitize_stack_category(item)
        for item in _list_of_dicts(payload.get("technology_stack_categories"))
    ]
    payload["system_components"] = [
        _sanitize_system_component(item)
        for item in _list_of_dicts(payload.get("system_components"))
    ]
    payload["tradeoffs"] = [
        _sanitize_tradeoff(item)
        for item in _list_of_dicts(payload.get("tradeoffs"))
    ]
    payload["assumptions"] = [
        _sanitize_assumption(item)
        for item in _list_of_dicts(payload.get("assumptions"))
    ]
    payload["open_questions"] = [
        _sanitize_missing_information(item)
        for item in _list_of_dicts(payload.get("open_questions"))
    ]
    payload["risks"] = [
        _sanitize_risk(item)
        for item in _list_of_dicts(payload.get("risks"))
    ]
    if isinstance(payload.get("reasoning"), dict):
        reasoning = payload["reasoning"]
        reasoning["summary"] = _sanitize_text(
            reasoning.get("summary"),
            "The architecture keeps Core v1 focused on local planning boundaries.",
        )
        reasoning["evidence"] = [
            text
            for item in reasoning.get("evidence", [])
            if isinstance(item, str)
            and (text := _sanitize_optional_text(item, None)) is not None
        ]
    return payload


def _sanitize_stack_category(item: dict[str, Any]) -> dict[str, Any]:
    item["name"] = _sanitize_text(item.get("name"), "Application Layer")
    item["recommendation"] = _sanitize_text(
        item.get("recommendation"),
        "Use a provider-neutral Core v1 application layer.",
    )
    item["rationale"] = _sanitize_text(
        item.get("rationale"),
        "Keeps architecture planning focused and reviewable.",
    )
    return item


def _sanitize_system_component(item: dict[str, Any]) -> dict[str, Any]:
    item["name"] = _sanitize_text(item.get("name"), "Core Application Component")
    item["responsibility"] = _sanitize_text(
        item.get("responsibility"),
        "Support Core v1 planning responsibilities within local boundaries.",
    )
    item["interactions"] = [
        text
        for value in item.get("interactions", [])
        if isinstance(value, str)
        and (text := _sanitize_optional_text(value, None)) is not None
    ]
    return item


def _sanitize_tradeoff(item: dict[str, Any]) -> dict[str, Any]:
    item["decision"] = _sanitize_text(item.get("decision"), "Keep Core v1 modular.")
    item["benefit"] = _sanitize_text(item.get("benefit"), "Keeps planning simple and reviewable.")
    item["cost"] = _sanitize_text(item.get("cost"), "Future expansion may require revisiting boundaries.")
    return item


def _sanitize_assumption(item: dict[str, Any]) -> dict[str, Any]:
    item["text"] = _sanitize_text(
        item.get("text"),
        "Core v1 architecture remains limited to local planning boundaries.",
    )
    if item.get("source") is not None:
        item["source"] = _sanitize_optional_text(item.get("source"), None)
    return item


def _sanitize_missing_information(item: dict[str, Any]) -> dict[str, Any]:
    item["question"] = _sanitize_text(
        item.get("question"),
        "Which Core v1 planning data needs should be clarified first?",
    )
    item["impact"] = _sanitize_text(
        item.get("impact"),
        "Affects architecture confidence and planning specificity.",
    )
    return item


def _sanitize_risk(item: dict[str, Any]) -> dict[str, Any]:
    item["description"] = _sanitize_text(
        item.get("description"),
        "Unclear planning boundaries could reduce architecture usefulness.",
    )
    if item.get("impact") is not None:
        item["impact"] = _sanitize_optional_text(item.get("impact"), None)
    if item.get("mitigation") is not None:
        item["mitigation"] = _sanitize_optional_text(item.get("mitigation"), None)
    return item


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value or [] if isinstance(item, dict)]


def _sanitize_optional_text(value: Any, fallback: str | None) -> str | None:
    if not isinstance(value, str):
        return fallback
    sanitized = _sanitize_text(value, fallback or "")
    return sanitized if sanitized else fallback


def _sanitize_text(value: Any, fallback: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    sentences = _split_sentences(value)
    kept = [sentence for sentence in sentences if not detect_architecture_forbidden_scope(sentence)]
    sanitized = " ".join(kept).strip()
    if not sanitized:
        return fallback
    return sanitized


def _split_sentences(value: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", value).strip()
    if not normalized:
        return []
    return re.split(r"(?<=[.!?])\s+", normalized)
