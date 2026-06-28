# Research: SprintPilot v2 Taiga Backlog Export

## Decision: Implement Taiga as an Isolated Integration Package

**Rationale**: The constitution requires separation between domain logic, integrations,
agent orchestration, data access, and presentation. A dedicated
`sprintpilot.integrations.taiga` package keeps Taiga-specific configuration, auth,
HTTP, mapping, and sync behavior away from Core v1 planning generation and LLM
provider abstractions.

**Alternatives considered**:

- Add Taiga export directly to the Core workflow: rejected because it would couple
  planning generation to an external system.
- Add Taiga export to reporting: rejected because report generation should remain a
  local presentation concern.

## Decision: Support Application Token and Bearer Token Auth Shapes

**Rationale**: The feature requires username/email or token-based auth and Taiga
application token / bearer token auth. v2 should support token-based configuration
without storing secrets in source control. Auth models can construct headers from
environment values while hiding token values from logs and results.

**Alternatives considered**:

- Password login flow: rejected for v2 because it increases credential handling and
  session lifecycle complexity.
- OAuth-style flow: rejected because it is not required by the current specification.

## Decision: Preserve Non-Taiga Fields in Descriptions or Source Metadata

**Rationale**: SprintPlan contains acceptance criteria, story point reasoning,
dependencies, risks, and reasoning that are important for review. Taiga may not expose
first-class fields for every SprintPilot concept, so v2 preserves those details in
backlog descriptions and source metadata while avoiding scheduling semantics.

**Alternatives considered**:

- Drop unsupported fields: rejected because it would reduce handoff usefulness.
- Add custom Taiga fields: rejected because it depends on project-specific Taiga
  administration and is not required for v2.

## Decision: Treat Idempotency as Best-Effort and Conservative

**Rationale**: SprintPilot can safely detect previously exported items when source
identifiers are embedded in Taiga item descriptions or metadata. Without those
identifiers, title matching is useful only when unambiguous. The sync layer should
prefer reporting ambiguity over linking to the wrong backlog item.

**Alternatives considered**:

- Full bidirectional sync state: rejected as out of scope and too large for a backlog
  export release.
- Always create new items: rejected because it would make retries unsafe.

## Decision: Use Dry Run as the Human Review Gate

**Rationale**: SprintPilot must preserve human review before important generated
artifacts are accepted, exported, or handed off. A dry-run mode gives users a concrete
preview of external mutations before write mode.

**Alternatives considered**:

- Prompt interactively before every created item: rejected because it complicates CLI
  automation and tests.
- Export immediately after Core v1 workflow completion: rejected because it removes
  review from the external mutation boundary.
