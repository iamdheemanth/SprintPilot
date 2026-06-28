# Implementation Plan: SprintPilot v2 Taiga Backlog Export

**Branch**: `002-taiga-backlog-export` | **Date**: 2026-06-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-taiga-backlog-export/spec.md`

## Summary

SprintPilot v2 adds a Taiga integration layer that exports existing Core v1 SprintPlan
artifacts into Taiga backlog epics, user stories, and tasks. The release is strictly
backlog-only: it does not assign sprint, milestone, velocity, capacity, or
multi-sprint scheduling information, and it does not alter Core v1 planning logic.

The technical approach is a small integration package under
`src/sprintpilot/integrations/taiga/` with separate modules for authentication,
configuration-facing models, HTTP client behavior, SprintPlan mapping, and sync
orchestration. Tests use mocked HTTP responses and fixture SprintPlan objects so the
Taiga integration remains independent from live credentials and the LLM provider
abstraction.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Pydantic for structured settings and payload models; pytest
for tests; Python standard-library HTTP or a minimal HTTP dependency already approved
by the project for outbound API calls

**Storage**: No database; optional local sync preview/result objects only. Taiga is the
external system of record for created backlog items.

**Testing**: pytest unit tests for config parsing, auth, mapper, validation, and sync
orchestration; mocked API tests for Taiga client and sync behavior

**Target Platform**: Local developer machine, command-line execution, and Python
library usage from existing SprintPilot workflow surfaces

**Project Type**: Single Python CLI application with modular integration package

**Performance Goals**: Export a typical SprintPlan with up to 5 epics, 25 stories, and
100 tasks in under 2 minutes after configuration is available, excluding Taiga service
latency outside SprintPilot control

**Constraints**: Backlog item creation only; no sprint assignment, milestone
assignment, capacity planning, velocity planning, multi-sprint scheduling, GitHub
integration, code generation, analytics, cloud collaboration, review agents, RAG, or
Core v1 planning behavior changes

**Scale/Scope**: Individual users and small teams exporting one completed SprintPlan
to one Taiga project at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Spec Traceability**: PASS. The plan maps directly to the v2 specification and only
  implements Taiga backlog export.
- **Human Review and Explainability**: PASS. Dry-run previews and sync results explain
  created, matched, skipped, failed, and unsupported mappings before or after mutation.
- **Agile Alignment**: PASS. The integration uses standard Agile concepts: epics, user
  stories, tasks, backlog, acceptance criteria, and story points as planning metadata.
- **Engineering Confidence Score**: PASS. v2 does not create or modify confidence
  scores. Existing Core v1 confidence behavior remains unchanged.
- **Modular Architecture**: PASS. Taiga config, auth, client, mapper, and sync logic
  remain isolated under an integration package and do not leak into LLM, scoring,
  reporting, or planning generation modules.
- **Quality and Testing**: PASS. The plan includes focused unit tests for mapping,
  validation, auth, config, dry-run, and mocked sync behavior.
- **Security and Privacy**: PASS. Credentials are read from environment variables and
  never stored in reports, source control, logs, or sync result payloads.
- **Scope Control**: PASS. Future modules remain excluded. Taiga v2 is a one-way
  backlog export, not scheduling, project management replacement, or bidirectional
  sync.

## High-Level System Architecture

SprintPilot v2 adds a narrow integration layer beside the Core v1 workflow:

1. **Configuration Layer**: Extends runtime settings with Taiga-specific values while
   keeping LLM provider settings untouched.
2. **Authentication Layer**: Resolves supported Taiga auth headers from environment
   variables and rejects unsupported or incomplete credential states.
3. **Client Layer**: Encapsulates Taiga HTTP operations for project resolution,
   existing-item lookup, and backlog epic/story/task creation.
4. **Mapper Layer**: Converts `SprintPlan` epics, stories, tasks, estimates,
   acceptance criteria, dependencies, risks, and reasoning into Taiga-safe payloads
   that explicitly exclude scheduling fields.
5. **Sync Layer**: Builds a reviewable sync plan, supports dry-run mode, performs
   conservative idempotent matching, creates backlog items in dependency order, and
   returns a sync result.
6. **Presentation/Workflow Boundary**: Existing CLI or workflow surfaces may call the
   sync service, but the integration remains independent from LLM providers, CrewAI,
   scoring, and Core v1 artifact generation.

## Major Modules and Components

- `sprintpilot.integrations`: Namespace package for external integrations.
- `sprintpilot.integrations.taiga.auth`: Taiga authentication modes, credential
  loading, and authorization header construction.
- `sprintpilot.integrations.taiga.client`: HTTP client interface and Taiga API
  operations used by sync.
- `sprintpilot.integrations.taiga.models`: Taiga settings, payloads, source metadata,
  sync actions, sync plans, and sync results.
- `sprintpilot.integrations.taiga.mapper`: SprintPlan-to-Taiga payload mapper and
  mapping validation.
- `sprintpilot.integrations.taiga.sync`: Orchestration for dry-run, idempotent lookup,
  create order, error handling, and result reporting.
- `sprintpilot.config`: Runtime settings extension for Taiga values loaded from
  environment variables without disrupting LLM settings.
- `sprintpilot.cli`: Optional command surface for invoking dry-run or real Taiga
  backlog export from existing SprintPilot outputs.

## Data Flow From SprintPlan to Taiga Backlog

1. User reviews Core v1 SprintPlan.
2. User provides Taiga configuration through environment variables or command options.
3. Runtime settings validate base URL, auth mode, credentials, and project identifier.
4. Sync service receives a validated `SprintPlan`, Taiga settings, and dry-run/write
   mode.
5. Mapper produces a `TaigaSyncPlan` containing epic, user story, and task actions.
6. Dry-run returns the sync plan with no Taiga mutation calls.
7. Write mode resolves the Taiga project and checks for existing items using
   SprintPilot source identifiers and conservative fallback matching.
8. Sync creates or matches epics, creates or matches user stories, then creates or
   matches tasks under the correct user stories.
9. Sync returns a `TaigaSyncResult` with created, matched, skipped, failed, and
   unsupported items plus reasoning.

## Backlog-Only Rules

- Taiga payloads MUST NOT include sprint, milestone, capacity, velocity, sprint order,
  or scheduled container fields.
- Story point estimates MAY be preserved as backlog metadata or description content,
  but MUST NOT trigger planning calculations or schedule assignment.
- Dependencies and sequencing MAY be preserved as description content, but MUST NOT
  split or assign stories across sprints.
- Any future desire to schedule work MUST require a new specification.

## Project Structure

### Documentation (this feature)

```text
specs/002-taiga-backlog-export/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── taiga-client-contract.md
│   └── taiga-sync-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
└── sprintpilot/
    ├── config.py
    ├── cli.py
    ├── domain/
    │   └── artifacts.py
    └── integrations/
        ├── __init__.py
        └── taiga/
            ├── __init__.py
            ├── auth.py
            ├── client.py
            ├── mapper.py
            ├── models.py
            └── sync.py

tests/
├── integration/
│   └── test_taiga_sync_workflow.py
└── unit/
    ├── test_taiga_auth.py
    ├── test_taiga_config.py
    ├── test_taiga_mapper.py
    ├── test_taiga_sync.py
    └── test_taiga_validation.py
```

**Structure Decision**: Use a single integration package under
`src/sprintpilot/integrations/taiga` so Taiga-specific concerns stay outside domain,
LLM provider abstraction, scoring, validation of Core v1 artifacts, report assembly,
and agent orchestration.

## Implementation Phases

### Phase 1: Integration Foundation

- Create integration package structure.
- Add Taiga runtime settings and validation.
- Add Taiga auth models for application-token and bearer-token flows.
- Define sync models, source metadata, actions, and results.

### Phase 2: Mapping and Validation

- Implement SprintPlan-to-Taiga payload mapping for epics, user stories, and tasks.
- Preserve acceptance criteria, estimate reasoning, dependencies, risks, and source
  identifiers in descriptions or metadata.
- Reject unsupported scheduling mappings and invalid story/task relationships.

### Phase 3: Client and Sync Orchestration

- Implement Taiga client methods for project resolution, existing backlog lookup, and
  item creation.
- Implement dry-run sync plan generation.
- Implement write-mode sync with conservative idempotent matching.
- Return explainable sync results.

### Phase 4: CLI/Workflow Surface

- Add a narrow export entrypoint that accepts existing SprintPlan artifacts and Taiga
  settings.
- Keep Core v1 planning generation unchanged.
- Keep CrewAI optional and unrelated to export.

### Phase 5: Quality Pass

- Add tests for config parsing, auth, mapping, dry-run, mocked API sync, and missing
  setting validation.
- Validate that no exported payload includes sprint, milestone, capacity, velocity, or
  scheduling fields.
- Update user-facing docs and quickstart.

## Risks and Assumptions

- **Taiga API shape variance**: Hosted Taiga and self-hosted versions may differ.
  Mitigation: keep client operations small and contract-tested with mocked responses.
- **Idempotency ambiguity**: Existing Taiga items may not contain SprintPilot metadata.
  Mitigation: prefer source identifiers; use title matching only when unambiguous.
- **Partial sync failure**: Network or permission errors can occur after some items are
  created. Mitigation: return detailed sync results and rely on idempotent reruns.
- **Scope creep into scheduling**: Backlog export could be mistaken for sprint
  planning automation. Mitigation: tests and mapper validation ban scheduling fields.
- **Credential safety**: Tokens could leak through logs. Mitigation: credential models
  never expose token values in repr, reports, or sync results.

## Testing Strategy

- Unit test Taiga settings parsing from environment values and explicit overrides.
- Unit test missing base URL, auth, and project identifier validation.
- Unit test auth header construction for application token and bearer token modes.
- Unit test mapper output for epics, user stories, tasks, acceptance criteria, story
  points, dependencies, risks, and source identifiers.
- Unit test that mapper and sync payloads exclude sprint, milestone, capacity,
  velocity, and scheduling fields.
- Unit test dry-run sync makes no create or update client calls.
- Unit test mocked API sync creates epics, then user stories, then tasks.
- Unit test idempotent matching for source identifiers and ambiguous title matches.
- Integration test an end-to-end sync workflow with mocked Taiga client responses.
- Do not require live Taiga credentials in automated tests.

## Clear v2 Boundaries

Included in SprintPilot v2:

- Taiga backlog export from existing SprintPlan artifacts
- Taiga epics, user stories, and tasks
- Taiga configuration and auth validation
- Dry-run preview
- Idempotent behavior where safe
- Mocked API tests
- Human-reviewable sync results

Excluded from SprintPilot v2:

- Sprint assignment
- Milestone assignment
- Capacity planning
- Velocity planning
- Multi-sprint scheduling
- Splitting stories across sprints
- GitHub integration
- Code generation or scaffolding
- Analytics
- Cloud collaboration
- Review agents
- RAG
- Bidirectional sync or Taiga import
- Changes to Core v1 planning logic unless strictly required for export-readable
  artifact access

## Complexity Tracking

No constitution violations require justification. The integration is intentionally
small, one-way, and backlog-only.
