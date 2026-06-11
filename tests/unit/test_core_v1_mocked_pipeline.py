from __future__ import annotations

from sprintpilot.domain import ArchitecturePlan, ProductDefinition, SprintPlan
from sprintpilot.llm import LLMProvider, LLMProviderConfig, LLMRequest, LLMResponse, StructuredGenerationResult
from sprintpilot.workflow.core import (
    run_architecture_planning_workflow,
    run_product_definition_workflow,
    run_sprint_planning_workflow,
)


class InternshipTrackerProvider(LLMProvider):
    @property
    def config(self) -> LLMProviderConfig:
        return LLMProviderConfig(provider_name="mock", model_name="mock-core-v1")

    def execute(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content="{}")

    def generate_structured(self, request: LLMRequest) -> StructuredGenerationResult:
        schema_name = (request.response_schema or {}).get("name")
        payloads = {
            "ProductDefinition": _product_definition_payload(),
            "ArchitecturePlan": _architecture_plan_payload(),
            "SprintPlan": _sprint_plan_payload(),
        }
        return StructuredGenerationResult(
            data=payloads[schema_name],
            raw_response=LLMResponse(content="{}", model=self.config.model_name),
        )


def _product_definition_payload() -> dict[str, object]:
    return {
        "summary": "A student internship tracking platform for organizing applications and progress.",
        "primary_users": ["students", "career advisors"],
        "functional_requirements": [
            {"id": "FR-001", "text": "System must let students record internship applications."},
            {"id": "FR-002", "text": "System must track each application status."},
        ],
        "non_functional_requirements": [
            {"id": "NFR-001", "text": "Outputs must be easy for students to review."}
        ],
        "user_stories": [
            {
                "id": "US-001",
                "title": "Track internship application",
                "priority": "P1",
                "actor": "student",
                "goal": "record an internship application",
                "benefit": "monitor progress and next steps",
                "acceptance_criteria": [
                    {
                        "given": "a student has internship details",
                        "when": "they add the application",
                        "then": "the application appears with a status",
                    }
                ],
            }
        ],
        "assumptions": [{"text": "Students manage one personal application list."}],
        "missing_information": [
            {"question": "Should advisors view student data?", "impact": "Affects permissions and scope."}
        ],
        "reasoning": {"summary": "The idea centers on reducing application-tracking ambiguity."},
    }


def _architecture_plan_payload() -> dict[str, object]:
    return {
        "recommended_architecture": "A modular local application with separated domain, workflow, validation and presentation boundaries.",
        "technology_stack_categories": [
            {"name": "Interface", "recommendation": "Local workflow surface", "rationale": "Keeps Core v1 focused."},
            {"name": "Domain", "recommendation": "Structured models", "rationale": "Supports validation and handoff."},
        ],
        "system_components": [
            {"name": "Application Tracker Domain", "responsibility": "Represent applications and statuses."},
            {"name": "Planning Workflow", "responsibility": "Coordinate product, architecture and sprint artifacts."},
        ],
        "database_considerations": "A simple persistent store may be needed in a later product implementation, but Core v1 only plans it.",
        "tradeoffs": [
            {
                "decision": "Keep planning local and modular.",
                "benefit": "Avoids premature integration complexity.",
                "cost": "Does not solve collaboration in Core v1.",
            }
        ],
        "assumptions": [{"text": "The first product version focuses on individual student tracking."}],
        "open_questions": [
            {"question": "Are reminders required?", "impact": "Could affect scheduling components."}
        ],
        "risks": [{"description": "Ambiguous advisor access could change architecture scope."}],
        "reasoning": {"summary": "The architecture separates planning concerns and preserves future extensibility."},
    }


def _sprint_plan_payload() -> dict[str, object]:
    return {
        "epics": [
            {"id": "EPIC-001", "title": "Application Tracking", "objective": "Help students track internship applications."}
        ],
        "stories": [
            {
                "id": "SP-001",
                "title": "Record internship application",
                "priority": "P1",
                "acceptance_criteria": [
                    "Given internship details, when a student records them, then the application is saved with status."
                ],
            }
        ],
        "tasks": [
            {"id": "TASK-001", "story_id": "SP-001", "description": "Define application fields and status values."},
            {"id": "TASK-002", "story_id": "SP-001", "description": "Validate required application details."},
        ],
        "story_point_estimates": [
            {"story_id": "SP-001", "points": 3, "reasoning": "A small first slice with one core entity and clear acceptance criteria."}
        ],
        "dependencies": [
            {"description": "Application status vocabulary must be agreed before task breakdown.", "impacts": ["SP-001"]}
        ],
        "assumptions": [{"text": "The first sprint targets manual application tracking only."}],
        "risks": [{"description": "Reminder and advisor features could expand scope if included too early."}],
        "reasoning": {"summary": "The sprint plan prioritizes a minimal application tracking increment."},
    }


def test_core_v1_mocked_pipeline_from_idea_to_sprint_plan() -> None:
    provider = InternshipTrackerProvider()

    product_definition = run_product_definition_workflow(
        product_idea="Build a student internship tracking platform.",
        provider=provider,
    )
    architecture_plan = run_architecture_planning_workflow(
        product_definition=product_definition,
        provider=provider,
    )
    sprint_plan = run_sprint_planning_workflow(
        product_definition=product_definition,
        architecture_plan=architecture_plan,
        provider=provider,
    )

    assert isinstance(product_definition, ProductDefinition)
    assert product_definition.summary
    assert product_definition.functional_requirements
    assert product_definition.user_stories[0].acceptance_criteria
    assert product_definition.assumptions
    assert product_definition.missing_information
    assert product_definition.reasoning.summary

    assert isinstance(architecture_plan, ArchitecturePlan)
    assert architecture_plan.system_components
    assert architecture_plan.technology_stack_categories
    assert architecture_plan.tradeoffs
    assert architecture_plan.assumptions
    assert architecture_plan.open_questions
    assert architecture_plan.reasoning.summary

    assert isinstance(sprint_plan, SprintPlan)
    assert sprint_plan.epics
    assert sprint_plan.stories
    assert sprint_plan.tasks
    assert sprint_plan.dependencies
    assert sprint_plan.story_point_estimates[0].points == 3
    assert sprint_plan.story_point_estimates[0].reasoning
