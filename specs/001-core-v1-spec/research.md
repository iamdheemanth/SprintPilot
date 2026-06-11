# Research: SprintPilot Core v1

## Decision: CLI-first local application

**Rationale**: A CLI is the smallest interface that supports the full Core v1 workflow:
idea intake, staged generation, confidence scoring and report output. It avoids
frontend complexity and deployment concerns while still producing a usable experience
for engineers, student developers, founders and small teams.

**Alternatives considered**:

- Lightweight local web app: better visual review experience, but adds frontend and
  local server complexity before Core v1 behavior is proven.
- Desktop app: unnecessary packaging and UI complexity for v1.
- Hosted web app: introduces deployment, accounts and collaboration concerns that are
  explicitly out of scope.

## Decision: Python 3.12 backend package

**Rationale**: Python supports fast iteration for AI orchestration, structured data
validation, CLI tooling and testing. A `src/sprintpilot` package keeps domain logic
importable and testable.

**Alternatives considered**:

- JavaScript/TypeScript: strong for web apps, but Core v1 does not need a frontend.
- Notebook/prototype script: fast, but poor modularity and task generation foundation.
- Multi-service architecture: unnecessary for a local single-user workflow.

## Decision: CrewAI for agent orchestration only

**Rationale**: CrewAI matches the requested multi-agent direction and can model Product
Manager, Architect and Scrum Master responsibilities. Keeping it behind adapters
prevents orchestration details from leaking into scoring, validation and reporting.

**Alternatives considered**:

- Direct LLM calls only: simpler, but less aligned with the requested agent model.
- Custom agent framework: avoidable complexity for Core v1.
- Autonomous coding agent architecture: explicitly out of scope.

## Decision: Pydantic-style structured domain models

**Rationale**: SprintPilot artifacts need predictable sections, validation, and
traceability. Structured models make report assembly, scoring, testing and future
interfaces cleaner.

**Alternatives considered**:

- Free-form markdown-only artifacts: easier to generate, but weak for scoring and
  validation.
- Database-backed records: unnecessary because Core v1 only needs local report output.

## Decision: Deterministic Engineering Confidence Score

**Rationale**: The constitution requires confidence scores with reasoning. A
deterministic scoring engine gives predictable, testable behavior while agent outputs
provide evidence. The score can evolve later without changing the workflow contract.

**Alternatives considered**:

- LLM-generated score only: too black-box and hard to test.
- Manual-only rubric: transparent, but less useful without automated factor analysis.
- Single unweighted score: simpler, but hides readiness drivers.

## Decision: Markdown report output for v1

**Rationale**: Markdown is readable, portable, easy to diff and sufficient for human
review and engineering handoff. It avoids PDF/export complexity and keeps the report
locally inspectable.

**Alternatives considered**:

- JSON-only output: useful for tools but poor as the primary review artifact.
- PDF generation: presentation polish, but unnecessary implementation scope.
- External project-management export: explicitly out of scope.

## Decision: Tests mock agent orchestration

**Rationale**: Automated tests must be reliable, fast and independent from provider
latency, credentials or changing model behavior. Mocked agent outputs let tests focus
on SprintPilot logic and contracts.

**Alternatives considered**:

- Live LLM calls in tests: realistic but slow, flaky and credential-dependent.
- No integration tests: too risky for a pipeline-oriented product.
