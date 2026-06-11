# Data Model: SprintPilot Core v1

## ProductIdea

Represents the user's raw planning input.

**Fields**:

- `title`: Optional short label inferred from or provided with the idea.
- `raw_text`: Required product idea text.
- `submitted_at`: Timestamp for traceability.
- `context_notes`: Optional user-provided constraints or notes.

**Validation Rules**:

- `raw_text` must not be empty.
- Ideas that request out-of-scope capabilities must still be accepted, but downstream
  artifacts must mark those requests as out of scope.

## Message

Provider-independent conversation message used for prompt execution.

**Fields**:

- `role`: Required role such as system, user, assistant or tool.
- `content`: Required message content.
- `metadata`: Optional provider-neutral metadata for future extensibility.

**Relationships**:

- Included in one `LLMRequest`.

**Validation Rules**:

- `content` must not be empty.
- Provider-specific fields must not be required by the domain model.

## LLMRequest

Provider-agnostic request for text or structured generation.

**Fields**:

- `messages`: Ordered list of `Message` values.
- `model`: Optional logical model name or configured model alias.
- `temperature`: Optional generation temperature.
- `max_tokens`: Optional output token limit.
- `response_schema`: Optional structured-output schema identifier or schema payload.
- `metadata`: Optional provider-neutral request metadata.

**Relationships**:

- Sent through one `LLMProvider` implementation.
- Used by agent adapters and orchestration code, not by domain scoring or reporting.

**Validation Rules**:

- Must include at least one message.
- Must not expose provider SDK request objects.
- Must support structured-generation requests without requiring a provider-specific
  SDK type.

## LLMResponse

Provider-agnostic response from prompt execution.

**Fields**:

- `content`: Generated response text.
- `model`: Model name or alias that produced the response when available.
- `finish_reason`: Provider-neutral completion reason when available.
- `usage`: Optional provider-neutral usage summary.
- `raw_metadata`: Optional provider-neutral metadata for diagnostics.

**Relationships**:

- Returned by one `LLMProvider`.
- May feed a `StructuredGenerationResult`.

**Validation Rules**:

- Must preserve generated content.
- Must not require provider-specific response classes.
- Must not include credentials or secrets.

## StructuredGenerationResult

Provider-independent result for parsed structured responses.

**Fields**:

- `data`: Parsed structured data payload.
- `raw_response`: Associated `LLMResponse`.
- `validation_errors`: Structured validation errors, if parsing failed.
- `is_valid`: Boolean validation status.

**Relationships**:

- Produced by agent adapters after an `LLMResponse`.
- Feeds domain artifact adapters for product definition, architecture plan and sprint
  plan.

**Validation Rules**:

- Must preserve the raw response for explainability and debugging.
- Must separate parsing failure from provider execution failure.

## LLMProviderConfig

Provider-neutral runtime configuration used by the LLM factory.

**Fields**:

- `provider_name`: Configured provider identifier.
- `model_name`: Configured model name or alias.
- `timeout_seconds`: Optional request timeout.
- `max_retries`: Optional retry count.
- `environment_keys`: Names of environment variables used for credentials.

**Relationships**:

- Used by the LLM factory to create one `LLMProvider` for Core v1.

**Validation Rules**:

- Credentials must be read from environment variables and must not be stored in the
  model.
- Core v1 supports a single configured provider; routing, benchmarking, fallback
  chains, cost tracking and latency tracking remain future capabilities.

## ProductDefinition

Structured product planning output produced from a ProductIdea.

**Fields**:

- `summary`: Product summary and value proposition.
- `primary_users`: Target users or personas.
- `functional_requirements`: Testable product capabilities.
- `non_functional_requirements`: Quality, reliability, performance, maintainability,
  extensibility, explainability and security expectations.
- `user_stories`: Agile user stories with priorities.
- `acceptance_criteria`: Criteria linked to user stories.
- `assumptions`: Assumptions used to resolve ambiguity.
- `missing_information`: Open questions or gaps.
- `reasoning`: Explanation for major requirement decisions.

**Relationships**:

- Created from one `ProductIdea`.
- Feeds one `ArchitecturePlan` and one `SprintPlan`.

**Validation Rules**:

- Must include at least one functional requirement.
- Must include at least one user story with acceptance criteria.
- Must separate assumptions from confirmed requirements.

## ArchitecturePlan

Planning-level architecture guidance based on the ProductDefinition.

**Fields**:

- `recommended_architecture`: High-level architecture description.
- `technology_stack_categories`: Suggested categories such as interface, application
  logic, storage, validation and testing.
- `system_components`: High-level components and responsibilities.
- `database_considerations`: Data persistence needs, if applicable.
- `tradeoffs`: Architecture tradeoffs and decision rationale.
- `assumptions`: Architecture-specific assumptions.
- `open_questions`: Information needed for higher confidence.
- `reasoning`: Explanation behind recommendations.

**Relationships**:

- Depends on one `ProductDefinition`.
- Feeds one `SprintPlan` and one `EngineeringConfidenceAssessment`.

**Validation Rules**:

- Must include reasoning for recommendations.
- Must not include deployment implementation, external integrations or code
  generation tasks as Core v1 capabilities.

## SprintPlan

Agile delivery planning artifact.

**Fields**:

- `epics`: Groups of related work.
- `stories`: Sprint-ready stories with priorities and acceptance criteria.
- `tasks`: Task breakdowns linked to stories.
- `story_point_estimates`: Estimates with reasoning and uncertainty.
- `dependencies`: Planning dependencies or sequencing constraints.
- `risks`: Sprint planning risks.
- `reasoning`: Explanation for sequencing and estimation decisions.

**Relationships**:

- Depends on `ProductDefinition` and `ArchitecturePlan`.
- Feeds one `EngineeringConfidenceAssessment`.

**Validation Rules**:

- Stories must use Agile terminology.
- Story point estimates must include reasoning.
- Tasks must not include autonomous coding, repository management, CI/CD, deployment,
  or external integration work unless future specifications explicitly add them.

## EngineeringConfidenceAssessment

Readiness evaluation for the generated planning package.

**Fields**:

- `overall_score`: Integer from 0 to 100.
- `factor_scores`: Scores for requirement clarity, architecture completeness,
  dependency readiness, acceptance criteria quality, technical ambiguity and delivery
  risk.
- `reasoning`: Factor-level explanations.
- `risks`: Risks reducing readiness.
- `missing_information`: Information needed to increase confidence.
- `recommendations`: Actions to improve readiness.

**Relationships**:

- Evaluates `ProductDefinition`, `ArchitecturePlan` and `SprintPlan`.
- Included in one `SprintPilotReport`.

**Validation Rules**:

- Score must be numeric and bounded from 0 to 100.
- Each factor must include reasoning.
- Scores below 90 must include at least one recommended action.

## SprintPilotReport

Consolidated human-reviewable report.

**Fields**:

- `product_idea`: Original ProductIdea.
- `product_definition`: Generated ProductDefinition.
- `architecture_plan`: Generated ArchitecturePlan.
- `sprint_plan`: Generated SprintPlan.
- `confidence_assessment`: EngineeringConfidenceAssessment.
- `scope_boundaries`: Included and excluded Core v1 capabilities.
- `generated_at`: Report generation timestamp.

**Relationships**:

- Contains exactly one artifact set for a single product idea run.

**Validation Rules**:

- Must preserve reasoning, assumptions, risks, missing information and recommended
  actions.
- Must clearly exclude future-module content when it appears in the user idea or
  generated artifacts.
