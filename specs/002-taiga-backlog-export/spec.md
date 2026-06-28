# Feature Specification: SprintPilot v2 Taiga Backlog Export

**Feature Branch**: `002-taiga-backlog-export`

**Created**: 2026-06-13

**Status**: Draft

**Input**: User description: "Create SprintPilot v2 as a Taiga backlog integration release. SprintPilot Core v1 is complete and released. It already generates ProductDefinition, ArchitecturePlan, SprintPlan, EngineeringConfidenceAssessment, and a Markdown report. Build SprintPilot v2 so it exports SprintPlan output into Taiga backlog items only. v2 must create Taiga backlog items only. Do not assign work to sprints, milestones, or capacity planning. Do not split stories across multiple sprints. Taiga integration scope: Epics, User stories, Tasks. Explicitly out of scope: Sprint assignment, Milestone assignment, Capacity planning, Velocity planning, Multi-sprint scheduling, GitHub integration, Code generation, Analytics, Cloud collaboration, Review agents, RAG, Any changes to Core v1 planning logic unless strictly required."

## Why v2 Matters

SprintPilot Core v1 turns an idea into reviewable planning artifacts. SprintPilot v2
closes the next delivery gap by moving the accepted SprintPlan into an execution
backlog in Taiga. This makes SprintPilot feel like a planning-to-execution tool while
preserving human control: v2 exports backlog items for review and refinement in Taiga,
but it does not schedule the work, assign it to sprints, or make capacity decisions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Export SprintPlan as Taiga Backlog Items (Priority: P1)

As a SprintPilot user with a completed Core v1 SprintPlan, I want to export the plan's
epics, user stories, and tasks into a Taiga project backlog so that the planning output
becomes actionable work items without manually recreating them.

**Why this priority**: This is the primary v2 value. Without backlog export, the Taiga
release does not connect SprintPilot planning to execution.

**Independent Test**: Use a valid SprintPlan and valid Taiga configuration, then verify
that SprintPilot creates matching Taiga epics, user stories, and tasks in the target
project backlog only, with no sprint, milestone, capacity, velocity, or scheduling data.

**Acceptance Scenarios**:

1. **Given** a SprintPlan contains epics, stories, tasks, acceptance criteria, story
   points, dependencies, risks, and reasoning, **When** the user runs a Taiga export,
   **Then** SprintPilot creates Taiga epics, user stories, and tasks that preserve the
   planning content needed for backlog refinement.
2. **Given** the SprintPlan includes story point estimates and sequencing
   dependencies, **When** SprintPilot maps the plan to Taiga payloads, **Then** those
   details are included only as backlog metadata or description content and are not
   used to schedule work into sprints or milestones.
3. **Given** Taiga returns created item identifiers, **When** the export completes,
   **Then** SprintPilot reports which epics, user stories, and tasks were created or
   matched for human review.

---

### User Story 2 - Validate Taiga Configuration Before Export (Priority: P2)

As a user preparing a Taiga export, I want SprintPilot to validate required Taiga
settings before making changes so that missing credentials or project identifiers are
caught early and explained clearly.

**Why this priority**: External exports require credentials and target project context.
Failing fast protects users from partial or confusing sync attempts.

**Independent Test**: Run Taiga export with each required setting missing in turn and
verify SprintPilot stops before any Taiga mutation while explaining the missing
configuration and how to correct it.

**Acceptance Scenarios**:

1. **Given** the Taiga base URL is missing, **When** the user requests export, **Then**
   SprintPilot stops before any network call and reports the missing base URL.
2. **Given** no supported Taiga authentication configuration is available, **When** the
   user requests export, **Then** SprintPilot stops before any mutation and reports the
   supported authentication options.
3. **Given** the Taiga project identifier is missing, **When** the user requests
   export, **Then** SprintPilot stops before any mutation and reports that the target
   project must be configured.

---

### User Story 3 - Preview Taiga Export With Dry Run (Priority: P3)

As a user reviewing the export, I want a dry-run mode that shows the Taiga backlog
items SprintPilot would create so that I can review mappings before writing to Taiga.

**Why this priority**: SprintPilot requires human review for important artifacts. A
dry run preserves that review gate for external backlog creation.

**Independent Test**: Run Taiga export in dry-run mode against a valid SprintPlan and
configuration, then verify no Taiga items are created while the output shows the epics,
user stories, tasks, and unsupported mappings that would be processed.

**Acceptance Scenarios**:

1. **Given** dry-run mode is enabled, **When** the user requests export, **Then**
   SprintPilot validates configuration and mapping, produces a reviewable preview, and
   makes no create or update calls to Taiga.
2. **Given** the SprintPlan contains fields that Taiga cannot represent directly,
   **When** dry-run mode is enabled, **Then** SprintPilot reports how those fields will
   be preserved or why the mapping is unsupported.
3. **Given** the preview identifies unsupported mappings, **When** the export finishes,
   **Then** SprintPilot exits without mutating Taiga and explains what must be changed
   before a real sync.

---

### User Story 4 - Avoid Duplicate Backlog Items Where Possible (Priority: P4)

As a user running exports more than once, I want SprintPilot to avoid creating obvious
duplicates where possible so that repeated runs do not clutter the Taiga backlog.

**Why this priority**: Backlog exports may be retried after configuration fixes or
review. Idempotent behavior reduces operational risk without requiring a full
bidirectional synchronization system.

**Independent Test**: Run export twice with the same SprintPlan and target project
using mocked Taiga responses, then verify the second run reuses or skips matched
existing backlog items where stable identifiers or titles make that possible.

**Acceptance Scenarios**:

1. **Given** a Taiga backlog already contains items created from the same SprintPlan,
   **When** SprintPilot exports the plan again, **Then** it matches existing items
   where possible instead of creating duplicates.
2. **Given** SprintPilot cannot confidently match an existing item, **When** the export
   runs, **Then** it reports the ambiguity instead of silently linking to the wrong
   item.
3. **Given** an existing Taiga item is matched, **When** SprintPilot syncs child tasks,
   **Then** tasks are created under the matched user story only when they are not
   already present.

### Edge Cases

- The SprintPlan is missing epics, stories, tasks, acceptance criteria, or story point
  reasoning.
- A SprintPlan story references an epic or task relationship that cannot be resolved.
- Taiga credentials are present but unauthorized for the target project.
- The configured project identifier does not resolve to an accessible Taiga project.
- Taiga communication fails partway through an export.
- Taiga contains existing items with the same title but without SprintPilot metadata.
- A SprintPlan includes scheduling language that could be mistaken for sprint or
  milestone assignment.
- Taiga payload fields have length or required-field constraints that the SprintPlan
  content violates.
- Network timeouts or rate limits occur during sync.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST add a Taiga integration layer with clean boundaries between
  configuration, authentication, Taiga communication, SprintPlan-to-Taiga mapping, and sync
  orchestration.
- **FR-002**: System MUST support configuration for Taiga base URL, Taiga
  username/email or token identity when needed, Taiga application token or bearer token
  authentication, and target project identifier.
- **FR-003**: System MUST validate required Taiga configuration before making Taiga
  mutation calls.
- **FR-004**: System MUST provide clear validation errors for missing base URL,
  unsupported authentication configuration, missing project identifier, invalid
  SprintPlan relationships, and unsupported mappings.
- **FR-005**: System MUST provide a Taiga client for Taiga calls needed to resolve
  projects and create or inspect backlog epics, user stories, and tasks.
- **FR-006**: System MUST map SprintPlan epics to Taiga backlog epic payloads.
- **FR-007**: System MUST map SprintPlan sprint-ready stories to Taiga backlog user
  story payloads.
- **FR-008**: System MUST map SprintPlan story tasks to Taiga task payloads linked to
  the appropriate Taiga user story.
- **FR-009**: System MUST preserve acceptance criteria, story point estimate reasoning,
  assumptions, dependencies, risks, and SprintPilot source identifiers in Taiga backlog
  item descriptions or metadata where Taiga does not provide first-class fields.
- **FR-010**: System MUST support dry-run mode that validates configuration and
  mappings, produces a reviewable sync preview, and does not create, update, assign, or
  schedule Taiga items.
- **FR-011**: System MUST support idempotent behavior where possible by detecting
  existing Taiga backlog items using stable SprintPilot source identifiers and safe
  fallback matching.
- **FR-012**: System MUST report created, matched, skipped, failed, and previewed items
  after a sync attempt.
- **FR-013**: System MUST never assign exported items to Taiga sprints, milestones, or
  capacity planning constructs.
- **FR-014**: System MUST never split a SprintPlan story across multiple Taiga sprints,
  milestones, or scheduled containers.
- **FR-015**: System MUST keep the provider-agnostic LLM abstraction intact and MUST
  NOT introduce Taiga dependencies into LLM, domain scoring, report generation, or Core
  v1 planning logic.
- **FR-016**: System MUST keep CrewAI optional and MUST NOT require CrewAI for Taiga
  export unless an existing Core v1 workflow already needs it.
- **FR-017**: System MUST avoid changes to Core v1 planning behavior unless strictly
  required to read existing SprintPlan artifacts for export.
- **FR-018**: System MUST include focused tests for config parsing, authentication,
  payload mapping, dry-run sync, mocked Taiga sync, and validation of missing Taiga
  settings.
- **FR-019**: System MUST provide reviewer-visible reasoning for sync decisions that
  affect created, matched, skipped, failed, or unsupported Taiga backlog items.
- **FR-020**: System MUST preserve human review before real Taiga mutations by making
  dry-run output available and by clearly distinguishing preview from write mode.

### Key Entities *(include if feature involves data)*

- **Taiga Configuration**: Runtime settings for base URL, authentication mode,
  credential environment keys, project identifier, timeout, retry behavior, and dry-run
  defaults.
- **Taiga Credentials**: Authentication material loaded from environment variables,
  including application token or bearer token values. Credentials are never stored in
  source control or sync reports.
- **Taiga Project Reference**: The configured target Taiga project identifier and any
  resolved project metadata needed for payload creation.
- **Taiga Epic Payload**: The backlog epic representation derived from a SprintPlan
  epic.
- **Taiga User Story Payload**: The backlog user story representation derived from a
  SprintPlan story.
- **Taiga Task Payload**: The task representation derived from a SprintPlan story task
  and linked to one Taiga user story.
- **Taiga Sync Plan**: A reviewable list of intended Taiga create, match, skip, or
  failure actions derived from the SprintPlan before mutation.
- **Taiga Sync Result**: The final sync outcome with created, matched, skipped,
  previewed, and failed item summaries plus reviewer-visible reasoning.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can export a valid Core v1 SprintPlan to Taiga backlog epics,
  user stories, and tasks in under 2 minutes after configuration is available.
- **SC-002**: 100% of exported items in automated tests contain no sprint assignment,
  milestone assignment, capacity, velocity, or multi-sprint scheduling fields.
- **SC-003**: At least 95% of valid SprintPlan epics, stories, and tasks in fixture
  tests produce corresponding Taiga payloads with preserved source identifiers and
  reviewable descriptions.
- **SC-004**: 100% of missing required Taiga configuration tests fail before any Taiga
  mutation is attempted.
- **SC-005**: Dry-run tests show 100% of intended create or match actions while making
  zero Taiga mutation calls.
- **SC-006**: Re-running sync with the same SprintPlan and mocked existing Taiga
  metadata avoids duplicate creation for at least 90% of items with stable SprintPilot
  source identifiers.
- **SC-007**: Users reviewing sync output can identify created, matched, skipped,
  previewed, failed, and unsupported items without reading logs.

## Scope Boundaries *(mandatory)*

- **In Scope**: Taiga configuration, Taiga authentication, Taiga client, mapping
  Core v1 SprintPlan epics/stories/tasks to Taiga backlog payloads, dry-run preview,
  idempotent matching where possible, sync orchestration, validation, and sync result
  reporting.
- **Out of Scope**: Sprint assignment, milestone assignment, capacity planning,
  velocity planning, multi-sprint scheduling, splitting stories across multiple
  sprints, GitHub integration, code generation, analytics, cloud collaboration, review
  agents, RAG, changes to Core v1 planning logic beyond export-readable artifact
  access, Taiga-to-SprintPilot import, bidirectional synchronization, project
  management replacement workflows, and automatic backlog prioritization.
- **Human Approval Gates**: Users must be able to inspect SprintPlan output before
  export and must be able to run dry-run preview before real Taiga mutations.
- **Explainability Requirements**: Sync previews and results must explain created,
  matched, skipped, failed, and unsupported mappings, including why items were matched
  or why export stopped.

## Assumptions

- SprintPilot Core v1 artifacts are already available as structured artifacts or as
  local artifacts that can be loaded without changing Core v1 planning
  generation behavior.
- Taiga project access and permissions are managed outside SprintPilot; v2 only
  validates that configured credentials can perform required backlog operations.
- Taiga remains the only external backlog integration included in v2.
- Initial idempotency relies on SprintPilot source identifiers embedded in descriptions
  or metadata plus conservative title matching when source identifiers are absent.
- Story point estimates from SprintPilot may be preserved in descriptions or supported
  Taiga fields, but they do not trigger capacity, velocity, sprint, or milestone logic.
- Automated tests use mocked Taiga responses and do not require live Taiga
  credentials.
