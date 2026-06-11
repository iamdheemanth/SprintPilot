# Quickstart: SprintPilot Core v1

This quickstart validates the planned local CLI workflow for SprintPilot Core v1.

## Prerequisites

- Python 3.12 available locally.
- Project dependencies installed.
- Runtime model provider environment variables configured.
- No GitHub, Taiga, repository, CI/CD, deployment, collaboration, analytics, review
  agent or RAG configuration is required.

## Configure Runtime

Create local environment configuration from `.env.example` and set the OpenRouter API
key. SprintPilot defaults to OpenRouter with a pinned free primary model and ordered
free fallback models:

```text
SPRINTPILOT_MODEL_PROVIDER=openrouter
SPRINTPILOT_MODEL_NAME=openai/gpt-oss-20b:free
SPRINTPILOT_FALLBACK_MODELS=nvidia/nemotron-nano-9b-v2:free,qwen/qwen3-next-80b-a3b-instruct:free,google/gemma-4-31b-it:free
SPRINTPILOT_MODEL_MAX_RETRIES=2
SPRINTPILOT_MODEL_TIMEOUT_SECONDS=120
OPENROUTER_API_KEY=...
```

Provider credentials must be supplied through environment variables and must not be
stored in source control.

## Run Core v1 Workflow

```text
sprintpilot plan --idea "A lightweight app that helps freelancers plan client projects before writing code."
```

Expected result:

- CLI accepts the product idea.
- Product Manager Agent generates product definition artifacts.
- Architect Agent generates architecture planning guidance.
- Scrum Master Agent generates epics, stories, task breakdowns and estimates.
- Engineering Confidence Engine calculates a numeric score with reasoning.
- CLI writes a local Markdown SprintPilot report.

## Run With a Local Idea File

```text
sprintpilot plan --idea-file examples/freelancer-project-planner.txt --output reports/
```

Expected result:

- The original idea is preserved in the report.
- The generated report includes product definition, architecture planning, sprint
  planning, confidence assessment, risks, missing information and recommended actions.

## Validate Human Review Expectations

Open the generated report and confirm:

- Recommendations include reasoning.
- Story point estimates include reasoning.
- Confidence score includes factor-level explanations.
- Assumptions and missing information are visible.
- The report does not include future-module implementation work.

## Validate Out-of-Scope Handling

Run an idea that asks for repository automation:

```text
sprintpilot plan --idea "Build a tool that plans my app and automatically opens GitHub pull requests."
```

Expected result:

- SprintPilot still produces Core v1 planning artifacts.
- GitHub pull request automation is marked out of scope.
- The confidence assessment highlights scope risk or missing information when relevant.
