# Data Model: SprintPilot v2 Taiga Backlog Export

## TaigaSettings

Configuration needed to export backlog items.

**Fields**:

- `base_url`: Required Taiga instance URL.
- `project_identifier`: Required project slug, numeric id, or configured project
  reference.
- `auth_mode`: Required supported auth mode, such as application token or bearer token.
- `username_or_email`: Optional identity value when required by the selected auth mode.
- `token_environment_key`: Required environment variable name containing the token.
- `timeout_seconds`: Optional positive request timeout.
- `max_retries`: Optional non-negative retry count.
- `dry_run`: Boolean export mode default.

**Validation Rules**:

- `base_url` must not be empty.
- `project_identifier` must not be empty.
- `auth_mode` must be supported.
- `token_environment_key` must resolve to a non-empty environment value before write
  mode.
- Token values must never appear in repr, logs, sync results, or docs.

## TaigaAuth

Resolved authentication material for Taiga client calls.

**Fields**:

- `mode`: Supported auth mode.
- `headers`: Safe header mapping for HTTP requests.
- `identity`: Optional username/email label without secret material.

**Validation Rules**:

- Must not expose raw token values through model serialization used for reporting.
- Must produce a valid authorization header for the selected auth mode.

## TaigaProjectRef

Resolved Taiga project target.

**Fields**:

- `identifier`: Original configured project identifier.
- `project_id`: Resolved Taiga project id.
- `name`: Optional project display name.
- `slug`: Optional project slug.

**Validation Rules**:

- `project_id` must be available before create calls.

## SprintPilotSourceRef

Source metadata that links a Taiga item back to SprintPilot.

**Fields**:

- `artifact_type`: `epic`, `story`, or `task`.
- `source_id`: SprintPilot artifact id.
- `source_title`: SprintPilot artifact title or description.
- `sprint_plan_id`: Optional stable plan identifier if available.

**Validation Rules**:

- `artifact_type` and `source_id` must not be empty.
- Source refs must not contain credentials.

## TaigaEpicPayload

Payload derived from a SprintPlan epic.

**Fields**:

- `subject`: Epic title.
- `description`: Objective, source metadata, related SprintPilot reasoning, and
  optional dependency/risk context.
- `project_id`: Resolved Taiga project id.
- `source_ref`: SprintPilot source reference.

**Validation Rules**:

- Must not contain sprint, milestone, capacity, velocity, or scheduling fields.
- Must include source metadata for idempotency.

## TaigaUserStoryPayload

Payload derived from a SprintPlan story.

**Fields**:

- `subject`: Story title.
- `description`: Acceptance criteria, story point estimate reasoning, assumptions,
  dependencies, risks, and source metadata.
- `project_id`: Resolved Taiga project id.
- `epic_ref`: Optional mapped Taiga epic reference when available.
- `source_ref`: SprintPilot source reference.

**Validation Rules**:

- Must not contain sprint, milestone, capacity, velocity, or scheduling fields.
- Acceptance criteria must remain reviewable.
- Story point data must not be used for capacity or velocity planning.

## TaigaTaskPayload

Payload derived from a SprintPlan story task.

**Fields**:

- `subject`: Task description or short title.
- `description`: Source metadata and related SprintPilot context.
- `project_id`: Resolved Taiga project id.
- `user_story_ref`: Required mapped Taiga user story reference.
- `source_ref`: SprintPilot source reference.

**Validation Rules**:

- Must link to exactly one Taiga user story.
- Must not contain sprint, milestone, capacity, velocity, or scheduling fields.

## TaigaSyncAction

A planned or executed sync action.

**Fields**:

- `action_type`: `create`, `match`, `skip`, `fail`, or `preview`.
- `item_type`: `epic`, `user_story`, or `task`.
- `source_ref`: SprintPilot source reference.
- `payload`: Optional Taiga payload for create or preview.
- `taiga_ref`: Optional existing or created Taiga item reference.
- `reasoning`: Reviewer-visible reason for the action.
- `error`: Optional safe error message.

**Validation Rules**:

- Failed and skipped actions must include reasoning.
- Errors must not include credentials.

## TaigaSyncPlan

Reviewable set of actions generated before mutation.

**Fields**:

- `project`: Taiga project reference or configured project identifier.
- `dry_run`: Whether the plan is preview-only.
- `epic_actions`: Planned epic actions.
- `story_actions`: Planned user story actions.
- `task_actions`: Planned task actions.
- `unsupported_mappings`: Unsupported or invalid mappings with explanations.

**Validation Rules**:

- Dry-run plans must be serializable without secrets.
- Unsupported scheduling mappings must stop write mode.

## TaigaSyncResult

Final outcome of a dry-run or write-mode sync.

**Fields**:

- `dry_run`: Whether no mutations were made.
- `created`: Created item summaries.
- `matched`: Existing matched item summaries.
- `skipped`: Skipped item summaries.
- `failed`: Failed item summaries.
- `previewed`: Previewed item summaries.
- `reasoning`: Overall explanation of sync decisions.

**Validation Rules**:

- Must distinguish previewed from created items.
- Must not include secrets.
- Must preserve enough detail for human review and safe retry.
