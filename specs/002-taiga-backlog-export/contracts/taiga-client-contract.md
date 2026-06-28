# Contract: Taiga Client

The Taiga client is the only module that performs Taiga HTTP calls. Sync and mapping
logic depend on this contract rather than constructing HTTP requests directly.

## Responsibilities

- Resolve a configured project identifier to a Taiga project reference.
- Search existing backlog epics, user stories, and tasks for idempotent matching.
- Create backlog epics.
- Create backlog user stories.
- Create tasks linked to user stories.
- Convert Taiga API failures into safe integration errors that do not expose secrets.

## Required Operations

### Resolve Project

**Input**: `TaigaSettings`, `TaigaAuth`

**Output**: `TaigaProjectRef`

**Failure Cases**:

- Project not found.
- Credentials unauthorized.
- Network or timeout failure.

### Find Existing Epic

**Input**: `TaigaProjectRef`, `SprintPilotSourceRef`, optional title

**Output**: Existing Taiga epic reference or an ambiguity result

**Rules**:

- Source identifier matches are preferred.
- Title fallback may be used only when one unambiguous match exists.

### Find Existing User Story

**Input**: `TaigaProjectRef`, `SprintPilotSourceRef`, optional title

**Output**: Existing Taiga user story reference or an ambiguity result

**Rules**:

- Must not search or match by sprint or milestone assignment.

### Find Existing Task

**Input**: `TaigaProjectRef`, mapped user story reference, `SprintPilotSourceRef`,
optional subject

**Output**: Existing Taiga task reference or an ambiguity result

**Rules**:

- Task matching is scoped to the mapped user story.

### Create Epic

**Input**: `TaigaEpicPayload`

**Output**: Created Taiga epic reference

**Rules**:

- Payload must not include scheduling fields.

### Create User Story

**Input**: `TaigaUserStoryPayload`

**Output**: Created Taiga user story reference

**Rules**:

- Payload must not include sprint, milestone, capacity, velocity, or scheduling fields.

### Create Task

**Input**: `TaigaTaskPayload`

**Output**: Created Taiga task reference

**Rules**:

- Payload must link to exactly one user story.
- Payload must not include scheduling fields.
