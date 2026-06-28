# Tasks: SprintPilot v2 Taiga Backlog Export

**Input**: Design documents from `/specs/002-taiga-backlog-export/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required by the specification and constitution for configuration parsing,
authentication, payload mapping, dry-run sync, mocked API sync, and validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the integration package skeleton and test fixture locations.

- [X] T001 Create Taiga integration package files in src/sprintpilot/integrations/__init__.py and src/sprintpilot/integrations/taiga/__init__.py
- [X] T002 Create placeholder Taiga modules in src/sprintpilot/integrations/taiga/auth.py, src/sprintpilot/integrations/taiga/client.py, src/sprintpilot/integrations/taiga/mapper.py, src/sprintpilot/integrations/taiga/models.py, and src/sprintpilot/integrations/taiga/sync.py
- [X] T003 [P] Add Taiga test fixture helpers in tests/unit/fixtures/test_taiga_sprint_plan.py
- [X] T004 [P] Add v2 documentation links to README.md without changing Core v1 behavior

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define shared models, settings, auth, and validation before any story-level sync behavior.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 [P] Add Taiga settings and sync models in src/sprintpilot/integrations/taiga/models.py
- [X] T006 [P] Add Taiga auth mode and safe header construction tests in tests/unit/test_taiga_auth.py
- [X] T007 Implement Taiga auth resolution in src/sprintpilot/integrations/taiga/auth.py
- [X] T008 [P] Add Taiga config parsing and missing setting tests in tests/unit/test_taiga_config.py
- [X] T009 Extend RuntimeSettings with optional Taiga settings in src/sprintpilot/config.py
- [X] T010 [P] Add validation tests for prohibited scheduling fields in tests/unit/test_taiga_validation.py
- [X] T011 Implement shared scheduling-field validation in src/sprintpilot/integrations/taiga/models.py
- [X] T012 Define Taiga client interface and safe error types in src/sprintpilot/integrations/taiga/client.py

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Export SprintPlan as Taiga Backlog Items (Priority: P1) MVP

**Goal**: Convert a valid SprintPlan into Taiga backlog epics, user stories, and tasks.

**Independent Test**: With mocked Taiga responses and valid configuration, sync creates or matches epics, then user stories, then tasks, and no payload includes scheduling fields.

### Tests for User Story 1

- [X] T013 [P] [US1] Add mapper tests for epic payloads in tests/unit/test_taiga_mapper.py
- [X] T014 [P] [US1] Add mapper tests for user story payloads with acceptance criteria and estimate reasoning in tests/unit/test_taiga_mapper.py
- [X] T015 [P] [US1] Add mapper tests for task payloads linked to user stories in tests/unit/test_taiga_mapper.py
- [X] T016 [P] [US1] Add mocked API sync test for create ordering in tests/unit/test_taiga_sync.py
- [X] T017 [P] [US1] Add integration sync workflow test with mocked Taiga client in tests/integration/test_taiga_sync_workflow.py

### Implementation for User Story 1

- [X] T018 [US1] Implement SprintPlan epic-to-Taiga payload mapping in src/sprintpilot/integrations/taiga/mapper.py
- [X] T019 [US1] Implement SprintPlan story-to-Taiga payload mapping in src/sprintpilot/integrations/taiga/mapper.py
- [X] T020 [US1] Implement SprintPlan task-to-Taiga payload mapping in src/sprintpilot/integrations/taiga/mapper.py
- [X] T021 [US1] Implement Taiga client project, epic, user story, and task create methods in src/sprintpilot/integrations/taiga/client.py
- [X] T022 [US1] Implement write-mode sync orchestration for epics, stories, and tasks in src/sprintpilot/integrations/taiga/sync.py
- [X] T023 [US1] Add sync result summaries for created, matched, skipped, and failed backlog items in src/sprintpilot/integrations/taiga/sync.py

**Checkpoint**: User Story 1 exports backlog items with mocked Taiga responses.

---

## Phase 4: User Story 2 - Validate Taiga Configuration Before Export (Priority: P2)

**Goal**: Stop unsafe exports before mutation when Taiga settings are incomplete or unsupported.

**Independent Test**: Each missing required setting fails before any Taiga mutation call and reports a clear error.

### Tests for User Story 2

- [X] T024 [P] [US2] Add missing base URL validation test in tests/unit/test_taiga_config.py
- [X] T025 [P] [US2] Add missing auth validation test in tests/unit/test_taiga_config.py
- [X] T026 [P] [US2] Add missing project identifier validation test in tests/unit/test_taiga_config.py
- [X] T027 [P] [US2] Add unsupported mapping validation tests in tests/unit/test_taiga_validation.py

### Implementation for User Story 2

- [X] T028 [US2] Implement Taiga settings validation errors in src/sprintpilot/integrations/taiga/models.py
- [X] T029 [US2] Implement RuntimeSettings.from_env Taiga parsing in src/sprintpilot/config.py
- [X] T030 [US2] Implement pre-mutation validation in src/sprintpilot/integrations/taiga/sync.py
- [X] T031 [US2] Ensure validation failures return safe messages without credentials in src/sprintpilot/integrations/taiga/auth.py and src/sprintpilot/integrations/taiga/sync.py

**Checkpoint**: Invalid Taiga configuration is blocked before mutation.

---

## Phase 5: User Story 3 - Preview Taiga Export With Dry Run (Priority: P3)

**Goal**: Provide a reviewable dry-run preview with zero Taiga mutations.

**Independent Test**: Dry-run mode returns preview actions for all valid mappings and the mocked client records no create or update calls.

### Tests for User Story 3

- [X] T032 [P] [US3] Add dry-run no-mutation test in tests/unit/test_taiga_sync.py
- [X] T033 [P] [US3] Add dry-run unsupported mapping report test in tests/unit/test_taiga_sync.py
- [X] T034 [P] [US3] Add dry-run result serialization test without secrets in tests/unit/test_taiga_sync.py

### Implementation for User Story 3

- [X] T035 [US3] Implement TaigaSyncPlan preview actions in src/sprintpilot/integrations/taiga/models.py
- [X] T036 [US3] Implement dry-run branch in src/sprintpilot/integrations/taiga/sync.py
- [X] T037 [US3] Add dry-run CLI or workflow entrypoint wiring in src/sprintpilot/cli.py
- [X] T038 [US3] Add dry-run output formatting that distinguishes previewed from created items in src/sprintpilot/cli.py

**Checkpoint**: Users can preview Taiga export without changing Taiga.

---

## Phase 6: User Story 4 - Avoid Duplicate Backlog Items Where Possible (Priority: P4)

**Goal**: Make repeated exports safe when source identifiers or unambiguous matches exist.

**Independent Test**: Running sync twice with mocked existing Taiga items matches existing epics, stories, and tasks instead of creating duplicates where safe.

### Tests for User Story 4

- [X] T039 [P] [US4] Add source-identifier idempotency tests in tests/unit/test_taiga_sync.py
- [X] T040 [P] [US4] Add ambiguous title match skip test in tests/unit/test_taiga_sync.py
- [X] T041 [P] [US4] Add existing task matching scoped to user story test in tests/unit/test_taiga_sync.py

### Implementation for User Story 4

- [X] T042 [US4] Implement existing epic lookup contract in src/sprintpilot/integrations/taiga/client.py
- [X] T043 [US4] Implement existing user story lookup contract in src/sprintpilot/integrations/taiga/client.py
- [X] T044 [US4] Implement existing task lookup contract in src/sprintpilot/integrations/taiga/client.py
- [X] T045 [US4] Implement conservative match-or-create behavior in src/sprintpilot/integrations/taiga/sync.py
- [X] T046 [US4] Add ambiguity reasoning to skipped sync actions in src/sprintpilot/integrations/taiga/sync.py

**Checkpoint**: Repeated exports avoid obvious duplicates and report ambiguous matches.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, scope verification, and final quality checks.

- [X] T047 [P] Update .env.example with Taiga environment variable names and secret-handling comments
- [X] T048 [P] Update docs or README usage section with dry-run-first Taiga export workflow in README.md
- [X] T049 Verify no Taiga code imports provider-specific LLM modules, CrewAI modules, scoring modules, or report assembly modules in src/sprintpilot/integrations/taiga/
- [X] T050 Verify generated Taiga payloads exclude sprint, milestone, capacity, velocity, and scheduling fields in tests/unit/test_taiga_mapper.py and tests/unit/test_taiga_validation.py
- [X] T051 Run focused v2 tests for config, auth, mapper, sync, validation, and mocked integration workflow in tests/unit/ and tests/integration/
- [X] T052 Run existing Core v1 unit tests that cover SprintPlan models and workflow boundaries in tests/unit/test_sprint_plan_models.py and tests/unit/test_sprint_planning_workflow.py
- [X] T053 Review specs/002-taiga-backlog-export/quickstart.md and specs/002-taiga-backlog-export/contracts/ for consistency with implemented behavior

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational and delivers the MVP export.
- **User Story 2 (Phase 4)**: Depends on Foundational and can proceed alongside US1 after shared models exist.
- **User Story 3 (Phase 5)**: Depends on mapping and sync plan models from US1.
- **User Story 4 (Phase 6)**: Depends on client and sync behavior from US1.
- **Polish (Phase 7)**: Depends on desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: MVP; can start after Foundational.
- **User Story 2 (P2)**: Can start after Foundational; strengthens safety before write mode.
- **User Story 3 (P3)**: Depends on mapping models and sync plan structure.
- **User Story 4 (P4)**: Depends on client lookup and sync orchestration.

### Parallel Opportunities

- Setup fixture and docs tasks marked [P] can run in parallel.
- Foundational tests for auth, config, and validation can run in parallel.
- Mapper tests for epics, stories, and tasks can run in parallel.
- Configuration validation tests can run in parallel.
- Dry-run tests can run in parallel.
- Idempotency tests can run in parallel.

## Parallel Example: User Story 1

```bash
Task: "Add mapper tests for epic payloads in tests/unit/test_taiga_mapper.py"
Task: "Add mapper tests for user story payloads with acceptance criteria and estimate reasoning in tests/unit/test_taiga_mapper.py"
Task: "Add mapper tests for task payloads linked to user stories in tests/unit/test_taiga_mapper.py"
Task: "Add mocked API sync test for create ordering in tests/unit/test_taiga_sync.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational models, auth, settings, and validation.
3. Complete Phase 3 mapping, client create operations, and write-mode sync with mocked API tests.
4. Stop and validate backlog-only behavior before adding dry-run and idempotency polish.

### Incremental Delivery

1. Add backlog export MVP.
2. Harden configuration validation.
3. Add dry-run review gate.
4. Add conservative idempotency.
5. Finalize docs and regression checks.

### Scope Guardrails

- Do not add sprint assignment.
- Do not add milestone assignment.
- Do not add capacity or velocity planning.
- Do not split stories across sprints.
- Do not change Core v1 planning generation unless artifact loading requires a narrow compatibility addition.
