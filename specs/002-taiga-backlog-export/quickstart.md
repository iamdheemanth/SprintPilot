# Quickstart: SprintPilot v2 Taiga Backlog Export

## Prerequisites

- SprintPilot Core v1 can generate a valid `SprintPlan` and write the normal planning
  outputs.
- A Taiga project exists and the user has permission to create backlog epics, user
  stories, and tasks.
- A Taiga token is available through an environment variable or OS secret store.

## Configure Taiga

Create a user-local Taiga profile once. The profile stores non-secret connection
data such as base URL, project identifier, auth mode and the token environment key.

```powershell
sprintpilot taiga-connect `
  --profile acme `
  --base-url https://taiga.example.com `
  --project my-project `
  --auth-mode bearer `
  --token-env-key SPRINTPILOT_TAIGA_TOKEN `
  --default
```

Profiles are stored in the platform user config directory:

- Windows: `%APPDATA%\SprintPilot\taiga-profiles.json`
- macOS/Linux: `$XDG_CONFIG_HOME/sprintpilot/taiga-profiles.json` or
  `~/.config/sprintpilot/taiga-profiles.json`

The active profile for a repository is stored in `.sprintpilot/taiga.json`. That file
contains only the profile name and no token values.

Set the token separately:

```powershell
$env:SPRINTPILOT_TAIGA_TOKEN="replace-with-token"
```

Application-token mode uses `--auth-mode application-token` with a token environment
key configured for that token. Legacy `SPRINTPILOT_TAIGA_BASE_URL`,
`SPRINTPILOT_TAIGA_PROJECT`, `SPRINTPILOT_TAIGA_AUTH_MODE` and
`SPRINTPILOT_TAIGA_TOKEN_ENV_KEY` values remain supported as a fallback, but `.env`
is not the normal place for Taiga base URL or project selection.

## Generate Planning Artifacts

Run the normal SprintPilot planning command before exporting to Taiga:

```powershell
sprintpilot plan `
  --idea "Build a student internship tracking platform" `
  --output reports `
  --title "Student Internship Tracking Platform"
```

The planning run writes both review and integration artifacts:

- `reports/student-internship-tracking-platform.md`: the Markdown report for human
  review.
- `reports/student-internship-tracking-platform.sprint-plan.json`: the structured
  SprintPlan JSON artifact for Taiga export.

If `--output` is a specific Markdown file, the SprintPlan artifact is written beside
that file with the same stem and the `.sprint-plan.json` suffix.

## Preview Export

Run the export in dry-run mode first. The preview must show the epics, user stories,
and tasks SprintPilot would create or match, with no Taiga mutations.

```powershell
sprintpilot taiga-export `
  --sprint-plan-file reports/student-internship-tracking-platform.sprint-plan.json `
  --dry-run
```

Expected dry-run behavior:

- Configuration is validated.
- SprintPlan mappings are validated.
- Epics, user stories, and tasks are listed as previewed, matched, skipped, failed, or
  unsupported.
- No Taiga create or update calls are made.
- No sprint or milestone assignment appears in the preview.

## Write Export

After reviewing the preview, run write mode to create backlog items.

```powershell
sprintpilot taiga-export `
  --sprint-plan-file reports/student-internship-tracking-platform.sprint-plan.json `
  --live
```

Expected write behavior:

- Project is resolved.
- Existing items are matched when safe.
- Missing epics are created first.
- Missing user stories are created next.
- Missing tasks are created under the correct user story.
- The result reports created, matched, skipped, and failed items.

## Verify Backlog-Only Scope

After export, inspect the Taiga project:

- Epics exist in the backlog.
- User stories exist in the backlog.
- Tasks are attached to user stories.
- No item was assigned to a sprint.
- No item was assigned to a milestone.
- No capacity or velocity planning was performed.
- No story was split across multiple sprints.

## Automated Validation

Run the focused v2 tests:

```powershell
pytest tests/unit/test_taiga_config.py tests/unit/test_taiga_auth.py tests/unit/test_taiga_mapper.py tests/unit/test_taiga_sync.py tests/unit/test_taiga_validation.py tests/integration/test_taiga_sync_workflow.py
```
