# CLI Contract: SprintPilot Core v1

## Command

```text
sprintpilot plan [OPTIONS]
```

## Purpose

Generate a structured SprintPilot Core v1 report from a product idea using the local
CLI workflow.

## Inputs

Exactly one product idea source is required:

- `--idea TEXT`: Product idea text entered directly.
- `--idea-file PATH`: Path to a local text file containing the product idea.

Optional settings:

- `--output PATH`: Directory or file path for the generated report.
- `--format markdown`: Report format. Core v1 supports Markdown as the primary human
  review artifact.
- `--title TEXT`: Optional report title.
- `--dry-run`: Validate inputs and configuration without running agent generation.

## Environment

- `SPRINTPILOT_MODEL_PROVIDER`: Runtime model provider identifier. Defaults to
  `openrouter`.
- `SPRINTPILOT_MODEL_NAME`: Runtime model name. Defaults to `openrouter/free`.
- `OPENROUTER_API_KEY` or `SPRINTPILOT_OPENROUTER_API_KEY`: OpenRouter credential
  loaded from environment variables only. Credentials must not be accepted as
  command-line arguments or written to reports.

## Successful Result

The command prints:

- Report output path.
- Engineering Confidence Score.
- Count of risks and missing-information items.
- Reminder that generated artifacts require human review.

Exit code: `0`

## Error Results

- Missing idea input: exit code `2`, user-facing validation message.
- Both `--idea` and `--idea-file` provided: exit code `2`, user-facing validation
  message.
- Missing model configuration: exit code `3`, configuration guidance without printing
  secrets.
- Agent output validation failure: exit code `4`, failed stage and missing fields.
- Report write failure: exit code `5`, output path and filesystem guidance.

## Scope Constraints

The CLI must not:

- Generate source code.
- Modify repositories.
- Create project-management tickets.
- Trigger CI/CD or deployment.
- Connect to GitHub, Taiga, analytics systems, RAG systems or collaboration services.
