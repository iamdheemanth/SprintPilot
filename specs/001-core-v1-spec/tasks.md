---
description: "Implementation task list for SprintPilot Core v1"
---

# Tasks: SprintPilot Core v1

**Input**: Design documents from `/specs/001-core-v1-spec/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required by the SprintPilot constitution for scoring systems, planning
logic, transformation pipelines, domain services, LLM provider abstraction, and
critical workflows. Test tasks are listed before implementation tasks in each phase.

**Organization**: Tasks are grouped by user story to enable independent implementation
and testing of each Core v1 increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or depends only on completed prerequisites
- **[Story]**: Maps the task to a user story from `spec.md`
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the Python CLI project and create the modular package structure from `plan.md`.

- [ ] T001 Create Python project metadata with package entrypoint and dependencies in `pyproject.toml`
- [ ] T002 Create package directories and root package marker in `src/sprintpilot/__init__.py`
- [x] T003 [P] Create test package markers in `tests/unit/__init__.py` and `tests/integration/__init__.py`
- [ ] T004 [P] Create local runtime configuration example in `.env.example`
- [ ] T005 [P] Create initial project usage overview in `README.md`
- [ ] T006 [P] Create reusable test fixtures marker in `tests/fixtures/.gitkeep`
- [x] T007 Configure pytest defaults and source-path discovery in `pyproject.toml`

**Checkpoint**: Project skeleton exists and imports can be resolved by tests.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared domain, LLM abstraction, validation, configuration and test fixtures that all user stories depend on.

**Critical**: No user story work should begin until this phase is complete.

- [x] T008 [P] Add shared artifact value models for assumptions, reasoning, risks, recommendations and missing information in `src/sprintpilot/domain/artifacts.py`
- [x] T009 [P] Add confidence value models for factors, score caps and assessments in `src/sprintpilot/domain/confidence.py`
- [ ] T010 [P] Add report container models for Core v1 report assembly in `src/sprintpilot/domain/report.py`
- [x] T011 Add public domain exports in `src/sprintpilot/domain/__init__.py`
- [x] T012 [P] Add unit tests for shared artifact model validation in `tests/unit/test_artifact_models.py`
- [x] T013 [P] Add unit tests for confidence model bounds and required reasoning in `tests/unit/test_confidence_engine.py`
- [x] T014 Implement runtime settings and environment loading in `src/sprintpilot/config.py`
- [x] T015 Add unit tests for runtime settings validation and secret-safe errors in `tests/unit/test_config.py`
- [x] T016 [P] Add provider-independent LLM model tests for `Message`, `LLMRequest`, `LLMResponse` and `StructuredGenerationResult` in `tests/unit/test_llm_models.py`
- [x] T017 [P] Add LLM provider interface contract tests for prompt execution and structured generation in `tests/unit/test_llm_provider_contract.py`
- [x] T018 [P] Add LLM factory tests for single configured provider resolution and unsupported provider errors in `tests/unit/test_llm_factory.py`
- [x] T019 Implement provider-independent LLM request, response, structured result and provider config models in `src/sprintpilot/llm/models.py`
- [x] T020 Implement provider-independent LLM exception types in `src/sprintpilot/llm/exceptions.py`
- [x] T021 Implement provider-agnostic `LLMProvider` interface for prompt execution, retries, structured response generation and provider metadata in `src/sprintpilot/llm/provider.py`
- [x] T022 Implement Core v1 LLM provider factory boundary without multi-provider routing in `src/sprintpilot/llm/factory.py`
- [x] T023 Export LLM abstraction public interfaces in `src/sprintpilot/llm/__init__.py`
- [x] T024 Implement Core v1 forbidden-scope constants and detection helpers in `src/sprintpilot/validation/scope.py`
- [x] T025 Add unit tests for GitHub, Taiga, code generation, analytics, cloud, review agent, RAG, deployment, CI/CD and multi-user scope detection in `tests/unit/test_scope_validation.py`
- [ ] T026 Implement cross-artifact validation helpers for required reasoning and human-reviewable sections in `src/sprintpilot/validation/artifacts.py`
- [ ] T027 Add unit tests for required reasoning and review-section validation in `tests/unit/test_artifact_validation.py`
- [ ] T028 [P] Add complete product idea fixture in `tests/fixtures/complete_idea.txt`
- [ ] T029 [P] Add vague product idea fixture in `tests/fixtures/vague_idea.txt`
- [ ] T030 [P] Add out-of-scope product idea fixture in `tests/fixtures/out_of_scope_idea.txt`

**Checkpoint**: Shared models, LLM abstraction, validation, configuration and fixtures are available for all user story work.

---

## Phase 3: User Story 1 - Turn an Idea into Product Definition (Priority: P1) MVP

**Goal**: A user can submit a product idea and receive a structured product definition with requirements, user stories, acceptance criteria, assumptions, missing information and reasoning.

**Independent Test**: Run product definition generation with a mocked Product Manager output and verify the resulting `ProductDefinition` contains summary, functional requirements, non-functional requirements, user stories, acceptance criteria, assumptions, missing information and reasoning without out-of-scope implementation work.

### Tests for User Story 1

- [x] T031 [P] [US1] Add ProductIdea and ProductDefinition domain tests in `tests/unit/test_product_definition_models.py`
- [x] T032 [P] [US1] Add Product Manager adapter parsing tests with valid and incomplete outputs in `tests/unit/test_product_manager_adapter.py`
- [x] T033 [P] [US1] Add Product Manager prompt scope tests in `tests/unit/test_product_manager_prompts.py`
- [x] T034 [P] [US1] Add product definition workflow tests with mocked `LLMProvider` output in `tests/unit/test_product_definition_workflow.py`

### Implementation for User Story 1

- [x] T035 [US1] Implement `ProductIdea`, `ProductDefinition`, `ProductRequirement`, `UserStory` and `AcceptanceCriterion` models in `src/sprintpilot/domain/artifacts.py`
- [x] T036 [US1] Implement product idea text and idea-file input normalization in `src/sprintpilot/workflow/core.py`
- [x] T037 [US1] Define Product Manager prompt template with Core v1 scope boundaries in `src/sprintpilot/agents/prompts.py`
- [x] T038 [US1] Implement Product Manager output adapter using `StructuredGenerationResult` in `src/sprintpilot/agents/adapters.py`
- [x] T039 [US1] Implement Product Manager CrewAI agent factory that receives an `LLMProvider` instead of provider SDK configuration in `src/sprintpilot/agents/crew.py`
- [x] T040 [US1] Implement product definition stage orchestration using the LLM abstraction in `src/sprintpilot/workflow/core.py`
- [x] T041 [US1] Add scope validation for Product Manager outputs in `src/sprintpilot/validation/scope.py`
- [x] T042 [US1] Add human-review metadata for product definition artifacts in `src/sprintpilot/domain/artifacts.py`

**Checkpoint**: User Story 1 can produce and validate product definition artifacts independently through provider-agnostic LLM contracts.

---

## Phase 4: User Story 2 - Generate Architecture Planning Guidance (Priority: P2)

**Goal**: A user with a product definition can receive architecture planning guidance with recommended architecture, technology stack categories, components, database considerations, tradeoffs, assumptions, open questions and reasoning.

**Independent Test**: Use a mocked ProductDefinition and Architect output to verify the architecture plan validates independently and preserves reasoning, tradeoffs, assumptions and open questions.

### Tests for User Story 2

- [x] T043 [P] [US2] Add ArchitecturePlan domain model tests in `tests/unit/test_architecture_plan_models.py`
- [x] T044 [P] [US2] Add Architect adapter parsing tests with valid and incomplete outputs in `tests/unit/test_architect_adapter.py`
- [x] T045 [P] [US2] Add Architect prompt scope and advisory-language tests in `tests/unit/test_architect_prompts.py`
- [x] T046 [P] [US2] Add architecture stage workflow tests with mocked ProductDefinition and `LLMProvider` output in `tests/unit/test_architecture_workflow.py`

### Implementation for User Story 2

- [x] T047 [US2] Implement `ArchitecturePlan`, `SystemComponent`, `StackCategory` and `ArchitectureTradeoff` models in `src/sprintpilot/domain/artifacts.py`
- [x] T048 [US2] Define Architect prompt template with advisory recommendations and Core v1 exclusions in `src/sprintpilot/agents/prompts.py`
- [x] T049 [US2] Implement Architect output adapter using `StructuredGenerationResult` in `src/sprintpilot/agents/adapters.py`
- [x] T050 [US2] Implement Architect CrewAI agent factory that receives an `LLMProvider` instead of provider SDK configuration in `src/sprintpilot/agents/crew.py`
- [x] T051 [US2] Implement architecture planning stage orchestration using the LLM abstraction in `src/sprintpilot/workflow/core.py`
- [x] T052 [US2] Add architecture completeness validation rules in `src/sprintpilot/validation/artifacts.py`
- [x] T053 [US2] Add scope validation for architecture plans in `src/sprintpilot/validation/scope.py`

**Checkpoint**: User Story 2 can produce and validate architecture planning artifacts after User Story 1.

---

## Phase 5: User Story 3 - Produce Sprint-Ready Planning Artifacts (Priority: P3)

**Goal**: A user with product and architecture artifacts can receive epics, sprint-ready stories, task breakdowns, story point estimates, dependencies, risks and estimate reasoning.

**Independent Test**: Use mocked product and architecture artifacts with a mocked Scrum Master output and verify the sprint plan uses Agile terminology, includes acceptance criteria and explains estimates.

### Tests for User Story 3

- [x] T054 [P] [US3] Add SprintPlan domain model tests in `tests/unit/test_sprint_plan_models.py`
- [x] T055 [P] [US3] Add Scrum Master adapter parsing tests with estimate reasoning validation in `tests/unit/test_scrum_master_adapter.py`
- [x] T056 [P] [US3] Add Agile terminology validation tests for epics, stories, tasks and points in `tests/unit/test_agile_validation.py`
- [x] T057 [P] [US3] Add sprint planning stage workflow tests with mocked upstream artifacts and `LLMProvider` output in `tests/unit/test_sprint_planning_workflow.py`

### Implementation for User Story 3

- [x] T058 [US3] Implement `SprintPlan`, `Epic`, `SprintStory`, `StoryTask`, `StoryPointEstimate` and `PlanningDependency` models in `src/sprintpilot/domain/artifacts.py`
- [x] T059 [US3] Define Scrum Master prompt template with Agile terminology and Core v1 exclusions in `src/sprintpilot/agents/prompts.py`
- [x] T060 [US3] Implement Scrum Master output adapter using `StructuredGenerationResult` in `src/sprintpilot/agents/adapters.py`
- [x] T061 [US3] Implement Scrum Master CrewAI agent factory that receives an `LLMProvider` instead of provider SDK configuration in `src/sprintpilot/agents/crew.py`
- [x] T062 [US3] Implement sprint planning stage orchestration using the LLM abstraction in `src/sprintpilot/workflow/core.py`
- [x] T063 [US3] Implement Agile terminology and estimate-reasoning validation in `src/sprintpilot/validation/artifacts.py`
- [x] T064 [US3] Add scope validation for sprint plan tasks in `src/sprintpilot/validation/scope.py`

**Checkpoint**: User Story 3 can produce sprint-ready planning artifacts after User Stories 1 and 2.

---

## Phase 6: User Story 4 - Assess Engineering Confidence (Priority: P4)

**Goal**: A user can receive a numeric Engineering Confidence Score with factor-level reasoning, risks, missing information and recommended actions.

**Independent Test**: Feed validated product, architecture and sprint artifacts into the confidence engine and verify scores, weights, caps, reason codes, risks, missing information and recommendations.

### Tests for User Story 4

- [x] T065 [P] [US4] Add confidence factor weighting tests in `tests/unit/test_confidence_engine.py`
- [x] T066 [P] [US4] Add confidence score cap tests for missing artifacts and out-of-scope content in `tests/unit/test_confidence_engine.py`
- [x] T067 [P] [US4] Add recommendation tests for scores below 90 in `tests/unit/test_confidence_recommendations.py`
- [x] T068 [P] [US4] Add incomplete upstream artifact tests in `tests/unit/test_confidence_inputs.py`

### Implementation for User Story 4

- [x] T069 [US4] Implement confidence factor definitions and weights in `src/sprintpilot/scoring/factors.py`
- [x] T070 [US4] Implement requirement clarity scoring in `src/sprintpilot/scoring/engine.py`
- [x] T071 [US4] Implement architecture completeness scoring in `src/sprintpilot/scoring/engine.py`
- [x] T072 [US4] Implement dependency readiness scoring in `src/sprintpilot/scoring/engine.py`
- [x] T073 [US4] Implement acceptance criteria quality scoring in `src/sprintpilot/scoring/engine.py`
- [x] T074 [US4] Implement technical ambiguity and delivery risk scoring in `src/sprintpilot/scoring/engine.py`
- [x] T075 [US4] Implement weighted total, score caps, reason codes and recommendations in `src/sprintpilot/scoring/engine.py`
- [x] T076 [US4] Integrate confidence assessment stage into the workflow without provider dependencies in `src/sprintpilot/workflow/core.py`
- [x] T077 [US4] Export scoring public interfaces in `src/sprintpilot/scoring/__init__.py`

**Checkpoint**: User Story 4 can score a validated planning package without agent calls or provider SDKs.

---

## Phase 7: User Story 5 - Review a Structured SprintPilot Report (Priority: P5)

**Goal**: A user can run the full Core v1 workflow and receive a local Markdown report with all required sections, explainability, human review markers and explicit v1 scope boundaries.

**Independent Test**: Complete the mocked end-to-end CLI workflow and verify the report includes all required schema sections, preserves reasoning and risks, prints the confidence score and rejects invalid CLI input combinations.

### Tests for User Story 5

- [ ] T078 [P] [US5] Add report schema rendering tests in `tests/unit/test_report_assembly.py`
- [ ] T079 [P] [US5] Add report scope-boundary tests in `tests/unit/test_report_scope_boundaries.py`
- [ ] T080 [P] [US5] Add CLI input contract tests for `--idea`, `--idea-file`, `--output`, `--format`, `--title` and `--dry-run` in `tests/integration/test_cli_workflow.py`
- [ ] T081 [P] [US5] Add full mocked Core v1 workflow integration test using a fake `LLMProvider` in `tests/integration/test_cli_workflow.py`

### Implementation for User Story 5

- [ ] T082 [US5] Implement `SprintPilotReport` assembly from all artifacts in `src/sprintpilot/domain/report.py`
- [ ] T083 [US5] Implement Markdown report renderer with required sections in `src/sprintpilot/reporting/markdown.py`
- [ ] T084 [US5] Implement local report file writing and safe filename handling in `src/sprintpilot/reporting/markdown.py`
- [ ] T085 [US5] Implement full Core v1 workflow orchestration from idea to report using the LLM factory in `src/sprintpilot/workflow/core.py`
- [ ] T086 [US5] Implement Typer CLI command and options from `contracts/cli-contract.md` in `src/sprintpilot/cli.py`
- [ ] T087 [US5] Implement Rich progress and final summary output in `src/sprintpilot/cli.py`
- [ ] T088 [US5] Implement CLI error handling and exit codes from `contracts/cli-contract.md` in `src/sprintpilot/cli.py`
- [ ] T089 [US5] Export report public interfaces in `src/sprintpilot/reporting/__init__.py`

**Checkpoint**: User Story 5 produces the local SprintPilot Core v1 report through the CLI using mocked or real provider-agnostic agent orchestration.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validate the complete Core v1 package, document local usage and remove accidental scope creep or provider coupling.

- [ ] T090 [P] Update README quickstart and Core v1 scope boundaries in `README.md`
- [ ] T091 [P] Add CLI example idea file for quickstart validation in `examples/freelancer-project-planner.txt`
- [ ] T092 [P] Add package-level exports and version metadata in `src/sprintpilot/__init__.py`
- [ ] T093 Run quickstart dry-run validation notes in `specs/001-core-v1-spec/quickstart.md`
- [ ] T094 Add final scope audit test for generated report text in `tests/integration/test_core_v1_scope_audit.py`
- [ ] T095 Add provider-coupling import audit test for domain, workflow, scoring, validation, reporting and agents in `tests/unit/test_provider_import_boundaries.py`
- [ ] T096 Add final performance smoke test for mocked report generation under 30 seconds in `tests/integration/test_cli_workflow.py`
- [ ] T097 Review test configuration and remove any live LLM dependency from automated test paths in `tests/conftest.py`
- [ ] T098 Run full test suite and record results in `specs/001-core-v1-spec/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup** has no dependencies.
- **Phase 2: Foundational** depends on Phase 1.
- **Phase 3: User Story 1** depends on Phase 2.
- **Phase 4: User Story 2** depends on Phase 3 because architecture planning requires product definition.
- **Phase 5: User Story 3** depends on Phase 4 because sprint planning requires product and architecture artifacts.
- **Phase 6: User Story 4** depends on Phase 5 because confidence scoring evaluates product, architecture and sprint artifacts.
- **Phase 7: User Story 5** depends on Phase 6 because the report includes all prior artifacts and the confidence assessment.
- **Phase 8: Polish** depends on all selected user stories.

### User Story Dependencies

- **US1**: Independent MVP after setup, foundation and the LLM abstraction.
- **US2**: Requires US1 product definition artifacts.
- **US3**: Requires US1 product definition and US2 architecture artifacts.
- **US4**: Requires US1, US2 and US3 artifacts for full confidence scoring.
- **US5**: Requires US1 through US4 for the complete report, but report rendering can be unit-tested with fixtures.

### Within Each User Story

- Write and verify tests fail before implementation.
- Implement provider-independent LLM contracts before agent adapters.
- Implement domain models before adapters.
- Implement prompts before CrewAI factories.
- Implement adapters before workflow stage integration.
- Implement validation before downstream scoring or report assembly.
- Complete each story checkpoint before moving to the next priority.

## Parallel Opportunities

- Setup tasks T003-T006 can run in parallel after T001-T002 are understood.
- Foundational domain, LLM model, validation and fixture tasks T008-T010, T012-T018 and T028-T030 can run in parallel.
- Test tasks inside each user story can run in parallel before implementation.
- Agent prompt tasks and adapter tests for US1-US3 can be prepared independently after foundational models and LLM contracts exist.
- Report rendering tests and CLI contract tests in US5 can run in parallel using fixtures and a fake `LLMProvider`.

## Parallel Examples

### Foundational LLM Abstraction

```text
Task: "T016 [P] Add provider-independent LLM model tests for Message, LLMRequest, LLMResponse and StructuredGenerationResult in tests/unit/test_llm_models.py"
Task: "T017 [P] Add LLM provider interface contract tests for prompt execution and structured generation in tests/unit/test_llm_provider_contract.py"
Task: "T018 [P] Add LLM factory tests for single configured provider resolution and unsupported provider errors in tests/unit/test_llm_factory.py"
```

### User Story 1

```text
Task: "T031 [P] [US1] Add ProductIdea and ProductDefinition domain tests in tests/unit/test_product_definition_models.py"
Task: "T032 [P] [US1] Add Product Manager adapter parsing tests with valid and incomplete outputs in tests/unit/test_product_manager_adapter.py"
Task: "T033 [P] [US1] Add Product Manager prompt scope tests in tests/unit/test_product_manager_prompts.py"
```

### User Story 2

```text
Task: "T043 [P] [US2] Add ArchitecturePlan domain model tests in tests/unit/test_architecture_plan_models.py"
Task: "T044 [P] [US2] Add Architect adapter parsing tests with valid and incomplete outputs in tests/unit/test_architect_adapter.py"
Task: "T045 [P] [US2] Add Architect prompt scope and advisory-language tests in tests/unit/test_architect_prompts.py"
```

### User Story 4

```text
Task: "T065 [P] [US4] Add confidence factor weighting tests in tests/unit/test_confidence_engine.py"
Task: "T066 [P] [US4] Add confidence score cap tests for missing artifacts and out-of-scope content in tests/unit/test_confidence_engine.py"
Task: "T067 [P] [US4] Add recommendation tests for scores below 90 in tests/unit/test_confidence_recommendations.py"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2, including the LLM abstraction.
2. Complete Phase 3 only.
3. Validate that a product idea can become a structured ProductDefinition with assumptions, missing information, user stories and acceptance criteria through provider-agnostic contracts.
4. Stop and review before adding architecture, sprint planning, confidence scoring or report generation.

### Incremental Delivery

1. **MVP foundation**: Setup, shared domain, validation and LLM abstraction.
2. **MVP artifact**: US1 product definition.
3. **Planning depth**: Add US2 architecture planning.
4. **Agile handoff**: Add US3 sprint planning.
5. **Readiness assessment**: Add US4 Engineering Confidence Score.
6. **Usable Core v1**: Add US5 Markdown report and CLI flow.

### Single-Developer Path

1. Finish all setup and foundational work first.
2. Complete one user story phase at a time in priority order.
3. Keep agent calls mocked through a fake `LLMProvider` in tests until the deterministic workflow is stable.
4. Run the full test suite after each story checkpoint.

## Notes

- Tasks intentionally exclude GitHub integration, Taiga integration, code generation,
  analytics, cloud collaboration, review agents, RAG, deployment and multi-user
  collaboration.
- The LLM abstraction intentionally does not implement multi-provider routing,
  benchmarking, fallback chains, cost tracking, latency tracking, cloud
  infrastructure, analytics or local model management in Core v1.
- CrewAI is used only behind adapter boundaries; provider access flows through
  `src/sprintpilot/llm`.
- Domain logic, workflow orchestration, scoring, validation, reporting and agent
  adapters must not import provider SDKs directly.
- Human review gates are represented by visible report sections and stage boundaries,
  not collaborative approval workflows.
- Automated tests must not require live LLM calls or provider credentials.
