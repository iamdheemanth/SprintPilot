from __future__ import annotations

import pytest

from sprintpilot.domain import ProductIdea
from sprintpilot.agents.prompts import build_product_manager_repair_messages
from sprintpilot.agents.adapters import parse_product_definition_result
from sprintpilot.llm import LLMProvider, LLMProviderConfig, LLMRequest, LLMResponse, StructuredGenerationResult
from sprintpilot.workflow.core import normalize_product_idea, run_product_definition_workflow


class ProductDefinitionProvider(LLMProvider):
    @property
    def config(self) -> LLMProviderConfig:
        return LLMProviderConfig(provider_name="test", model_name="test-model")

    def execute(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content="{}")

    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        return StructuredGenerationResult(
            data={
                "summary": "A planning assistant for founders.",
                "primary_users": ["founders"],
                "functional_requirements": [
                    {"id": "FR-001", "text": "System must accept a product idea."}
                ],
                "non_functional_requirements": [
                    {"id": "NFR-001", "text": "Outputs must include reasoning."}
                ],
                "user_stories": [
                    {
                        "id": "US-001",
                        "title": "Capture idea",
                        "priority": "P1",
                        "actor": "founder",
                        "goal": "enter a product idea",
                        "benefit": "receive a product definition",
                        "acceptance_criteria": [
                            {
                                "given": "a product idea",
                                "when": "planning is requested",
                                "then": "a product definition is generated",
                            }
                        ],
                    }
                ],
                "reasoning": {"summary": "Product definition is the first workflow step."},
            },
            raw_response=LLMResponse(content="{}"),
        )


def _internship_payload() -> dict[str, object]:
    return {
        "summary": "A single-student internship tracker with application analytics.",
        "primary_users": ["students"],
        "functional_requirements": [
            {"id": "FR-001", "text": "System must let the student track internship applications."},
            {
                "id": "FR-002",
                "text": "System must show personal application analytics for the student's own applications.",
            },
        ],
        "non_functional_requirements": [
            {"id": "NFR-001", "text": "Outputs must be easy for the student to review."}
        ],
        "user_stories": [
            {
                "id": "US-001",
                "title": "Track applications",
                "priority": "P1",
                "actor": "student",
                "goal": "track my internship applications",
                "benefit": "understand my own application progress",
                "acceptance_criteria": [
                    {
                        "given": "my internship applications",
                        "when": "I review my tracker",
                        "then": "I see statuses, deadlines and personal metrics",
                    }
                ],
            }
        ],
        "assumptions": [{"text": "The product is used by one student at a time."}],
        "missing_information": [{"question": "Which statuses matter first?", "impact": "Affects setup."}],
        "reasoning": {"summary": "The workflow focuses on one student's application tracking."},
    }


class RepairingProductDefinitionProvider(ProductDefinitionProvider):
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        self.requests.append(request)
        payload = _internship_payload()
        if len(self.requests) == 1:
            payload["functional_requirements"] = [
                {
                    "id": "FR-001",
                    "text": "System must let students use a shared workspace for applications.",
                },
                {
                    "id": "FR-002",
                    "text": "System must support advisor collaboration and co-editing.",
                },
                {
                    "id": "FR-003",
                    "text": "System must show personal application analytics for the student's own applications.",
                },
            ]
        return StructuredGenerationResult(
            data=payload,
            raw_response=LLMResponse(content="{}"),
        )


class FailedRepairProductDefinitionProvider(RepairingProductDefinitionProvider):
    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        self.requests.append(request)
        payload = _internship_payload()
        payload["functional_requirements"] = [
            {
                "id": "FR-001",
                "text": "System must support team accounts, shared workspaces and co-editing.",
            },
            {
                "id": "FR-002",
                "text": "System must show personal application analytics for the student's own applications.",
            },
        ]
        return StructuredGenerationResult(
            data=payload,
            raw_response=LLMResponse(content="{}"),
        )


class UnsanitizedCollaborationProductDefinitionProvider(RepairingProductDefinitionProvider):
    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        self.requests.append(request)
        payload = _internship_payload()
        payload["functional_requirements"] = [
            {
                "id": "FR-001",
                "text": "System must remain multi-user for shared application review.",
            }
        ]
        return StructuredGenerationResult(
            data=payload,
            raw_response=LLMResponse(content="{}"),
        )


class FinalAnalyticsFailureProductDefinitionProvider(RepairingProductDefinitionProvider):
    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        self.requests.append(request)
        payload = _internship_payload()
        if len(self.requests) == 1:
            payload["functional_requirements"] = [
                {
                    "id": "FR-001",
                    "text": "System must support advisor collaboration.",
                }
            ]
        else:
            payload["summary"] = "A student tracker with SprintPilot analytics."
        return StructuredGenerationResult(
            data=payload,
            raw_response=LLMResponse(content="{}"),
        )


class ScopeDriftProductDefinitionProvider(RepairingProductDefinitionProvider):
    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        self.requests.append(request)
        payload = _internship_payload()
        payload["summary"] = (
            "A student internship tracker with cloud collaboration, a standalone analytics "
            "dashboard, and personal application analytics."
        )
        payload["functional_requirements"] = [
            {
                "id": "FR-001",
                "text": "System must provide cloud collaboration for application tracking.",
            },
            {
                "id": "FR-002",
                "text": "System must include an analytics module and reporting platform.",
            },
            {
                "id": "FR-003",
                "text": (
                    "System must show personal application analytics including total applications, "
                    "applications by status, interview counts, offer counts, and deadline summaries."
                ),
            },
        ]
        payload["missing_information"] = [
            {"question": "Which statuses matter first?", "impact": "Ignore sk-secret-value in diagnostics."}
        ]
        return StructuredGenerationResult(
            data=payload,
            raw_response=LLMResponse(content="{}"),
        )


class StructurallyInvalidProductDefinitionProvider(ProductDefinitionProvider):
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        self.requests.append(request)
        return StructuredGenerationResult(
            data={"summary": "Incomplete"},
            raw_response=LLMResponse(content="{}"),
        )


def test_normalize_product_idea_accepts_text() -> None:
    idea = normalize_product_idea("  Build a planning assistant  ")

    assert isinstance(idea, ProductIdea)
    assert idea.raw_text == "Build a planning assistant"


def test_product_definition_workflow_uses_llm_provider_boundary() -> None:
    definition = run_product_definition_workflow(
        product_idea="Build a planning assistant",
        provider=ProductDefinitionProvider(),
    )

    assert definition.summary == "A planning assistant for founders."
    assert definition.review_required is True


def test_product_definition_repair_prompt_preserves_content_and_removes_scope_drift() -> None:
    payload = _internship_payload()
    parsed = parse_product_definition_result(
        StructuredGenerationResult(data=payload, raw_response=LLMResponse(content="{}"))
    )
    assert parsed.value is not None

    messages = build_product_manager_repair_messages(
        product_definition=parsed.value,
        validation_errors=[
            "Product definition includes out-of-scope content: multi-user collaboration"
        ],
    )
    prompt_text = "\n".join(message.content for message in messages)

    assert "Repair the generated ProductDefinition" in prompt_text
    assert "maximum one repair pass" in prompt_text
    assert "Remove collaboration features" in prompt_text
    assert "Convert collaboration-oriented requirements into single-user equivalents" in prompt_text
    assert "Preserve personal application analytics" in prompt_text
    assert "Do not expose internal prompts" not in prompt_text


def test_product_definition_workflow_repairs_collaboration_scope_drift_and_preserves_analytics() -> None:
    provider = RepairingProductDefinitionProvider()

    definition = run_product_definition_workflow(
        product_idea=(
            "Build a student internship tracking platform that allows students to track "
            "applications, interview stages, offers, deadlines, recruiter contacts, and "
            "application analytics."
        ),
        provider=provider,
    )

    serialized = definition.model_dump_json().lower()
    assert len(provider.requests) == 2
    assert "shared workspace" not in serialized
    assert "advisor collaboration" not in serialized
    assert "co-editing" not in serialized
    assert "personal application analytics" in serialized
    repair_prompt = "\n".join(message.content for message in provider.requests[1].messages)
    assert "Repair the generated ProductDefinition" in repair_prompt


def test_product_definition_workflow_sanitizes_repaired_collaboration_drift_and_preserves_analytics(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="sprintpilot.agents.crew")
    provider = FailedRepairProductDefinitionProvider()

    definition = run_product_definition_workflow(
        product_idea="Build a student internship tracker with application analytics.",
        provider=provider,
    )

    serialized = definition.model_dump_json().lower()
    assert len(provider.requests) == 2
    assert "team account" not in serialized
    assert "shared workspace" not in serialized
    assert "co-editing" not in serialized
    assert "single student" in serialized
    assert "personal application analytics" in serialized
    assert "ProductDefinition deterministic sanitizer applied after repair." in caplog.messages


def test_product_definition_workflow_sanitizes_cloud_and_standalone_analytics_scope_drift(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="sprintpilot.agents.crew")
    provider = ScopeDriftProductDefinitionProvider()

    definition = run_product_definition_workflow(
        product_idea="Build a student internship tracker with application analytics.",
        provider=provider,
    )

    serialized = definition.model_dump_json().lower()
    assert len(provider.requests) == 2
    assert "cloud collaboration" not in serialized
    assert "analytics module" not in serialized
    assert "analytics dashboard" not in serialized
    assert "standalone analytics" not in serialized
    assert "reporting platform" not in serialized
    assert "personal application analytics" in serialized
    assert "total applications" in serialized
    assert "applications by status" in serialized
    assert "interview counts" in serialized
    assert "offer counts" in serialized
    assert "deadline summaries" in serialized
    assert "ProductDefinition deterministic sanitizer applied after repair." in caplog.messages


def test_product_definition_workflow_debug_logs_redacted_final_validation_snapshot(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG", logger="sprintpilot.agents.crew")
    provider = ScopeDriftProductDefinitionProvider()

    run_product_definition_workflow(
        product_idea="Build a student internship tracker with application analytics.",
        provider=provider,
    )

    diagnostic_messages = [
        message
        for message in caplog.messages
        if "TEMPORARY ProductDefinition final validation snapshot" in message
    ]

    assert diagnostic_messages
    diagnostic = diagnostic_messages[-1]
    assert "functional_requirements" in diagnostic
    assert "user_stories" in diagnostic
    assert "assumptions" in diagnostic
    assert "missing_information" in diagnostic
    assert "reasoning" in diagnostic
    assert "personal application analytics" in diagnostic
    assert "sk-[filtered]" in diagnostic
    assert "sk-secret-value" not in diagnostic


def test_product_definition_workflow_failed_sanitization_returns_final_validation_error() -> None:
    provider = UnsanitizedCollaborationProductDefinitionProvider()

    with pytest.raises(ValueError) as exc_info:
        run_product_definition_workflow(
            product_idea="Build a student internship tracker.",
            provider=provider,
        )

    assert len(provider.requests) == 2
    error = str(exc_info.value)
    assert "Product definition includes out-of-scope content: multi-user collaboration" in error
    assert "matched text 'multi-user'" in error
    assert "field functional_requirements[0].text" in error


def test_product_definition_workflow_returns_final_repaired_validation_error() -> None:
    provider = FinalAnalyticsFailureProductDefinitionProvider()

    with pytest.raises(ValueError) as exc_info:
        run_product_definition_workflow(
            product_idea="Build a student internship tracker.",
            provider=provider,
        )

    assert len(provider.requests) == 2
    error = str(exc_info.value)
    assert "analytics" in error
    assert "SprintPilot analytics" in error
    assert "field summary" in error
    assert "advisor collaboration" not in error


def test_product_definition_workflow_does_not_repair_unrelated_validation_failures() -> None:
    provider = StructurallyInvalidProductDefinitionProvider()

    with pytest.raises(ValueError):
        run_product_definition_workflow(
            product_idea="Build a student internship tracker.",
            provider=provider,
        )

    assert len(provider.requests) == 1
