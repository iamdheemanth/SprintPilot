# Implementation Plan: SprintPilot Core v1

**Branch**: `001-core-v1-spec` | **Date**: 2026-06-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-core-v1-spec/spec.md`

## Summary

SprintPilot Core v1 will be a CLI-first Python application that turns a product idea
into reviewable Agile SDLC planning artifacts: product definition, architecture plan,
sprint plan, Engineering Confidence Score and a structured report. The implementation
will keep deterministic domain logic separate from CrewAI-based agent orchestration so
future interfaces and integrations can be added without rewriting the core workflow.

The v1 experience is intentionally small: a user provides a product idea, SprintPilot
runs a staged planning workflow, writes a report to local output and keeps each
generated section explainable and human-reviewable. No external product integrations,
source code generation, deployment automation, collaboration, analytics, review agents,
or RAG system are included.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: CrewAI for agent orchestration behind adapters; Pydantic for
structured artifact and provider-agnostic LLM request/response models; Typer for CLI
commands; Rich for readable CLI output; pytest for tests

**Storage**: Local filesystem only for generated reports and optional run artifacts;
no database in Core v1

**Testing**: pytest unit tests for domain models, scoring, validators and report
assembly; integration tests for CLI workflow with mocked agent outputs

**Target Platform**: Local developer machine, command-line execution

**Project Type**: Single Python CLI application with modular domain, orchestration,
scoring and presentation packages

**Performance Goals**: Produce a complete report for a typical small-product idea in
under 30 seconds after generation starts, excluding variability from external model
provider latency when applicable

**Constraints**: Must run without GitHub, Taiga, repository access, CI/CD, deployment
configuration, multi-user collaboration, RAG, analytics or code generation; generated
outputs must remain explainable and reviewable

**Scale/Scope**: Individual users and small teams; one product idea per run; local
single-user workflow; Core v1 planning artifacts only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Spec Traceability**: PASS. The plan maps directly to Core v1 requirements for
  product idea intake, product definition, architecture planning, sprint planning,
  confidence scoring and report generation. Future modules are excluded.
- **Human Review and Explainability**: PASS. Each artifact is modeled with assumptions,
  reasoning, risks, missing information and recommendations. CLI output and local
  reports keep generated sections visible before final use.
- **Agile Alignment**: PASS. Sprint planning outputs use epics, user stories,
  acceptance criteria, story points, task breakdowns, dependencies and handoff
  language from the specification.
- **Engineering Confidence Score**: PASS. The score is implemented as a deterministic
  domain service with factor-level scoring, weights, reasoning, risks and readiness
  recommendations.
- **Modular Architecture**: PASS. Domain models, scoring logic, orchestration, report
  generation, CLI presentation and runtime configuration are separate modules with
  explicit boundaries.
- **Quality and Testing**: PASS. Scoring, validation, transformation and report
  assembly are covered by unit tests. The CLI workflow is covered by integration tests
  using mocked agent outputs.
- **Security and Privacy**: PASS. Secrets are read from environment variables only.
  Core v1 does not persist credentials or require external product integrations.
- **Scope Control**: PASS. GitHub, Taiga, code generation, analytics, cloud
  collaboration, review agents, RAG, deployment and multi-user collaboration remain
  explicitly out of scope.

## High-Level System Architecture

SprintPilot Core v1 uses a small layered architecture:

1. **Presentation Layer**: CLI command accepts a product idea and options for output
   location and report format.
2. **Application Layer**: Workflow service coordinates the Core v1 pipeline and
   enforces stage order and reviewable artifact boundaries.
3. **Agent Orchestration Layer**: CrewAI crews run the Product Manager, Architect, and
   Scrum Master responsibilities behind explicit adapter interfaces.
4. **Domain Layer**: Pydantic models define product, architecture, sprint, confidence,
   and report artifacts.
5. **Scoring Layer**: Engineering Confidence Score evaluates structured artifacts using
   deterministic factors, weights and reason codes.
6. **Report Layer**: Report assembler produces a structured local report from validated
   artifacts.
7. **LLM Provider Abstraction Layer**: Provider-agnostic request, response, message,
   structured generation, factory and exception contracts isolate provider SDKs and
   model configuration from SprintPilot business logic.
8. **Configuration Layer**: Runtime settings load provider credentials, output paths,
   and model configuration from environment variables or CLI options.

CrewAI is not allowed to own business rules. Agent output must be parsed and validated
into domain models before scoring or report generation.

SprintPilot domain logic, workflow orchestration, scoring, validation, reporting, and
agent adapters must depend on `sprintpilot.llm` interfaces rather than OpenAI,
Anthropic, Gemini, Ollama, OpenRouter, CrewAI provider configuration or any provider
SDK directly.

## Major Modules and Components

- `sprintpilot.cli`: CLI entrypoint, argument parsing, progress output and command
  result presentation.
- `sprintpilot.config`: Runtime settings, environment variable loading and validation.
- `sprintpilot.domain`: Structured models for product ideas, generated artifacts,
  confidence assessments, reports, risks, assumptions and recommendations.
- `sprintpilot.llm`: Provider-agnostic LLM request/response models, provider
  interface, provider factory and provider exceptions.
- `sprintpilot.agents`: Agent definitions, prompt templates, CrewAI crew setup, and
  agent output adapters.
- `sprintpilot.workflow`: Core orchestration service that executes stages in order and
  returns a complete planning package.
- `sprintpilot.scoring`: Engineering Confidence Score factors, weights, scoring
  rules, reason codes and recommendations.
- `sprintpilot.reporting`: Markdown report assembly and local file writing.
- `sprintpilot.validation`: Cross-artifact validation, scope checks, Agile terminology
  checks and completeness checks.
- `tests.unit`: Fast tests for domain and scoring behavior.
- `tests.integration`: End-to-end CLI workflow tests using mocked agent responses.

## Agent Responsibilities

### Product Manager Agent

- Accepts the product idea and user context.
- Produces product summary, primary users, functional requirements, non-functional
  requirements, user stories, acceptance criteria, assumptions and missing
  information.
- Must not generate code, integration tasks, deployment steps or future-module scope.

### Architect Agent

- Accepts the validated product definition.
- Produces recommended architecture, technology stack categories, high-level system
  components, database considerations, tradeoffs, assumptions and open questions.
- Must keep recommendations advisory and explain tradeoffs.
- Must not connect to repositories, inspect code, create code or include deployment
  architecture beyond planning-level considerations.

### Scrum Master Agent

- Accepts product definition and architecture plan.
- Produces epics, sprint-ready stories, task breakdowns, story point estimates,
  dependencies and estimate reasoning.
- Must use standard Agile terminology and keep stories independently understandable.
- Must not create Jira/Taiga tickets or integrate with external planning tools.

### Engineering Confidence Engine

- Not an autonomous agent in Core v1.
- Deterministic scoring service that evaluates validated artifacts.
- Produces numeric score, factor-level reasoning, risks, missing information, and
  recommended readiness actions.

## Data Flow From Input to Final Report

1. User runs the CLI with a product idea or points to a local text file containing the
   idea.
2. CLI creates a `ProductIdea` object and passes it to the workflow service.
3. Workflow resolves an `LLMProvider` through the LLM factory using runtime
   configuration.
4. Workflow invokes Product Manager orchestration through the agent adapter, which uses
   provider-agnostic LLM contracts and validates output into a `ProductDefinition`.
5. Workflow invokes Architect orchestration with the product definition and validates
   output into an `ArchitecturePlan`.
6. Workflow invokes Scrum Master orchestration with product and architecture artifacts
   and validates output into a `SprintPlan`.
7. Confidence scoring service evaluates `ProductDefinition`, `ArchitecturePlan`, and
   `SprintPlan` into an `EngineeringConfidenceAssessment`.
8. Report assembler combines all artifacts into a `SprintPilotReport`.
9. CLI writes the report locally and prints the output path plus the confidence score.

Human review gates are represented as explicit report sections and stage boundaries.
Core v1 does not implement collaborative approval workflows.

## Engineering Confidence Score Design

The score is a 0-100 integer composed from factor scores. Each factor includes a score,
weight, reasoning, evidence, risks and recommendations.

| Factor | Weight | Evaluation Focus |
|--------|--------|------------------|
| Requirement clarity | 25% | Clear functional requirements, user stories, acceptance criteria, assumptions |
| Architecture completeness | 20% | Architecture description, components, data considerations, tradeoffs |
| Dependency readiness | 15% | Known dependencies, external assumptions, missing decisions |
| Acceptance criteria quality | 15% | Testable story-level acceptance criteria and scope boundaries |
| Technical ambiguity | 15% | Unresolved unknowns, conflicting requirements, vague architecture areas |
| Delivery risk | 10% | Complexity, sequencing risk, estimate uncertainty, blocked decisions |

Scoring rules:

- Each factor returns 0-100 with a reason code and explanation.
- Weighted total is rounded to the nearest integer.
- Missing critical artifacts cap the total score at 60.
- Out-of-scope generated content caps the total score at 70 and emits a scope-risk
  recommendation.
- Conflicting requirements cap requirement clarity at 50 until resolved.
- Every score must include at least one action that could improve readiness when the
  total score is below 90.

## Project Structure

### Documentation (this feature)

```text
specs/001-core-v1-spec/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli-contract.md
│   └── report-schema.md
└── tasks.md
```

### Source Code (repository root)

```text
pyproject.toml
README.md
.env.example

src/
└── sprintpilot/
    ├── __init__.py
    ├── cli.py
    ├── config.py
    ├── domain/
    │   ├── __init__.py
    │   ├── artifacts.py
    │   ├── confidence.py
    │   └── report.py
    ├── llm/
    │   ├── __init__.py
    │   ├── provider.py
    │   ├── models.py
    │   ├── factory.py
    │   └── exceptions.py
    ├── agents/
    │   ├── __init__.py
    │   ├── crew.py
    │   ├── prompts.py
    │   └── adapters.py
    ├── workflow/
    │   ├── __init__.py
    │   └── core.py
    ├── scoring/
    │   ├── __init__.py
    │   ├── engine.py
    │   └── factors.py
    ├── reporting/
    │   ├── __init__.py
    │   └── markdown.py
    └── validation/
        ├── __init__.py
        ├── artifacts.py
        └── scope.py

tests/
├── integration/
│   └── test_cli_workflow.py
└── unit/
    ├── test_artifact_models.py
    ├── test_confidence_engine.py
    ├── test_llm_models.py
    ├── test_llm_provider_contract.py
    ├── test_llm_factory.py
    ├── test_report_assembly.py
    └── test_scope_validation.py
```

**Structure Decision**: Use a single Python package under `src/sprintpilot` with
separate domain, orchestration, workflow, scoring, reporting, validation and CLI
modules. This keeps Core v1 simple while leaving clear extension points for future
interfaces or integrations.

The `src/sprintpilot/llm` package is a required boundary. It supports a single
configured provider in Core v1, but its contracts must be broad enough to support
future provider switching, fallback chains, cost tracking, latency tracking, model
routing and local models without changing domain logic, scoring, validation,
reporting or workflow code.

## Implementation Phases

### Phase 1: Project Foundation

- Initialize Python project metadata and package structure.
- Add dependency configuration for CLI, validation, CrewAI orchestration and tests.
- Add runtime settings and `.env.example` for AI provider configuration.
- Create base domain models for all Core v1 artifacts.
- Create provider-independent LLM request, response, structured generation, provider
  interface, factory and exception contracts.

### Phase 2: Deterministic Domain and Scoring Core

- Implement artifact validation and scope-boundary checks.
- Implement Engineering Confidence Score factors, weights, caps, reason codes, and
  recommendations.
- Add unit tests for score calculations, missing-artifact behavior and scope risks.

### Phase 3: Agent Orchestration Adapters

- Define Product Manager, Architect and Scrum Master agent prompts and expected
  structured outputs.
- Implement CrewAI orchestration behind adapter interfaces.
- Connect CrewAI adapters to the `sprintpilot.llm` provider abstraction instead of
  provider SDKs or provider-specific configuration.
- Validate agent outputs into domain models before downstream use.
- Add tests using mocked agent responses rather than live model calls.

### Phase 4: Workflow and Report Generation

- Implement the Core v1 workflow service from idea intake through report assembly.
- Implement Markdown report generation with visible assumptions, risks, reasoning, and
  confidence details.
- Add integration tests for the full local workflow using mocked orchestration.

### Phase 5: CLI Experience and Quality Pass

- Implement CLI command for running the Core v1 workflow.
- Add readable progress and final report path output.
- Validate quickstart instructions.
- Run unit and integration tests.
- Review generated artifacts for Agile terminology, explainability and v1 scope.

## Risks and Assumptions

- **Agent output variability**: LLM-generated output may drift from the expected shape.
  Mitigation: validate every agent output into structured models and fail with clear
  messages when required fields are missing.
- **CrewAI dependency behavior**: CrewAI orchestration may introduce setup complexity.
  Mitigation: keep all orchestration behind adapters, route provider access through
  `sprintpilot.llm` and test with mocks.
- **Provider coupling**: Early implementation could accidentally couple agents or
  workflows to a specific LLM SDK. Mitigation: add provider-contract tests and import
  boundaries that keep provider-specific code out of domain, scoring, validation,
  reporting, workflow and agent adapter logic.
- **Score trustworthiness**: Users may over-trust a numeric score. Mitigation: always
  include factor reasoning, risks, missing information and recommended actions.
- **Scope creep pressure**: Users may expect GitHub, Taiga, code generation, analytics,
  or collaboration. Mitigation: scope validator and report language explicitly exclude
  future modules.
- **Provider latency or failures**: AI provider calls can be slow or fail. Mitigation:
  expose clear error messages and keep deterministic services independent of provider
  calls.
- **No persistence beyond local files**: Core v1 does not manage historical projects.
  Assumption: local report output is enough for the first implementation.

## Testing Strategy

- Unit test all domain models, validators and report assembly behavior.
- Unit test LLM request/response models, provider interface behavior, factory
  resolution and provider-independent exceptions.
- Unit test confidence factor scoring, weighting, caps, recommendations and edge
  cases for missing or conflicting artifacts.
- Unit test scope validation against banned Core v1 capabilities.
- Integration test CLI workflow using mocked Product Manager, Architect and Scrum
  Master outputs.
- Add fixture examples for a complete idea, a vague idea and an out-of-scope idea.
- Do not require live LLM calls in automated tests.
- Do not require provider SDKs or provider credentials in tests for domain, scoring,
  validation, reporting, workflow or CLI behavior.
- Validate quickstart steps manually before considering Core v1 implementation ready.

## Clear v1 Boundaries

Included in Core v1:

- Product idea intake
- Product definition artifacts
- Architecture planning artifacts
- Sprint planning artifacts
- Engineering Confidence Score
- Structured local report generation
- CLI-first local workflow
- Provider-agnostic LLM abstraction layer
- Human-reviewable generated output
- Explainability for recommendations, estimates, risks and scores

Excluded from Core v1:

- GitHub integration
- Taiga integration
- Code generation or scaffolding
- Autonomous coding
- Repository management
- CI/CD
- Analytics
- Cloud collaboration
- Review agents
- RAG systems
- Multi-user collaboration
- Production deployment concerns

## Complexity Tracking

No constitution violations require justification. The plan uses the simplest viable
local architecture for Core v1 while preserving modular boundaries for future versions.
