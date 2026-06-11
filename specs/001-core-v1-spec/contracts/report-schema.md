# Report Schema Contract: SprintPilot Core v1

Core v1 reports are human-reviewable Markdown documents assembled from structured
artifacts. The report must preserve the following top-level sections in order.

## Required Sections

1. `# SprintPilot Report: {title}`
2. `## Original Product Idea`
3. `## Product Definition`
4. `## Architecture Plan`
5. `## Sprint Plan`
6. `## Engineering Confidence Assessment`
7. `## Risks`
8. `## Missing Information`
9. `## Recommended Actions`
10. `## Scope Boundaries`

## Product Definition Section

Must include:

- Product summary.
- Primary users.
- Functional requirements.
- Non-functional requirements.
- User stories.
- Acceptance criteria.
- Assumptions.
- Reasoning.

## Architecture Plan Section

Must include:

- Recommended architecture.
- Suggested technology stack categories.
- High-level system components.
- Database considerations when applicable.
- Tradeoffs.
- Assumptions.
- Open questions.
- Reasoning.

## Sprint Plan Section

Must include:

- Epics.
- Sprint-ready stories.
- Task breakdown.
- Story point estimates.
- Dependencies.
- Estimate reasoning.

## Engineering Confidence Assessment Section

Must include:

- Overall numeric score from 0 to 100.
- Factor scores for requirement clarity, architecture completeness, dependency
  readiness, acceptance criteria quality, technical ambiguity and delivery risk.
- Factor-level reasoning.
- Score caps or warnings, if applied.

## Scope Boundaries Section

Must list Core v1 included capabilities and explicitly excluded capabilities:

- GitHub integration.
- Taiga integration.
- Code generation or scaffolding.
- Autonomous coding.
- Repository management.
- CI/CD.
- Analytics.
- Cloud collaboration.
- Review agents.
- RAG systems.
- Multi-user collaboration.
- Production deployment concerns.

## Validation Rules

- Reports must not contain credentials or secrets.
- Reports must preserve assumptions and missing information instead of silently
  resolving them.
- Reports must label out-of-scope requests as excluded rather than turning them into
  Core v1 implementation tasks.
