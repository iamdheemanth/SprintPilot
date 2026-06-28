# Contract: Taiga Sync Service

The sync service orchestrates SprintPlan export into Taiga backlog items. It owns
validation, dry-run behavior, idempotent matching, create ordering, and result
reporting.

## Input

- A validated Core v1 `SprintPlan`.
- Validated `TaigaSettings`.
- A `dry_run` flag.
- A Taiga client implementation.

## Output

- `TaigaSyncResult` for dry-run and write mode.

## Required Behavior

1. Validate Taiga settings before mutation.
2. Validate SprintPlan-to-Taiga mapping before mutation.
3. Build a reviewable sync plan.
4. In dry-run mode, return preview actions and make no create or update calls.
5. In write mode, resolve the project before creating items.
6. Match existing epics before creating new epics.
7. Match existing user stories before creating new user stories.
8. Match existing tasks under their mapped user stories before creating new tasks.
9. Return created, matched, skipped, failed, and previewed item summaries.
10. Stop write mode when unsupported scheduling mappings or invalid relationships are
    detected.

## Prohibited Behavior

- Do not assign sprint fields.
- Do not assign milestone fields.
- Do not perform capacity planning.
- Do not perform velocity planning.
- Do not split a SprintPlan story across multiple sprints.
- Do not call LLM providers.
- Do not require CrewAI.
- Do not alter Core v1 planning outputs.

## Error Handling

- Missing configuration errors stop before any Taiga client mutation.
- Mapping errors stop before any Taiga client mutation.
- Per-item Taiga failures are captured in the result and do not expose credentials.
- Partial sync results must include enough item references for a user to retry safely.
