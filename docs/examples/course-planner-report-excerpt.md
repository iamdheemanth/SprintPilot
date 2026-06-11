# Sample Report Excerpt: Course Planner

_This is a compact example of the kind of planning artifact SprintPilot Core v1 is designed to produce._

## Original Product Idea

Build a course planner that helps students organize required classes, prerequisites, semester schedules, credit loads and graduation progress.

## Product Definition

**Summary:** A student course planning tool that helps users map degree requirements, understand prerequisite chains, plan semester schedules and identify graduation progress gaps.

**Functional requirements:**

- FR-001: Students can add courses with credits, terms offered, requirement category and prerequisite information.
- FR-002: Students can build semester plans and see total credit load per term.
- FR-003: Students can identify unmet prerequisites before adding a course to a semester.
- FR-004: Students can review progress against graduation requirements.

**Assumptions:**

- Core v1 planning assumes manual course entry rather than a university system integration.
- Degree requirements are represented as user-maintained planning data.
- The first release supports one student workspace.

## Architecture Plan

**Recommended architecture:** A local-first planning application with explicit domain models for courses, prerequisites, terms, schedules and requirement groups.

**Tradeoffs:**

- Use structured prerequisite rules early: improves planning accuracy, but requires careful validation.
- Start with manual requirement entry: avoids integrations, but increases initial setup effort.
- Keep graduation progress explainable: improves user trust, but requires visible reasoning for unmet requirements.

## Sprint Plan

**Epics:**

- EPIC-001: Course Catalog Foundation
- EPIC-002: Semester Schedule Planning
- EPIC-003: Graduation Progress Review

**Sprint-ready stories:**

- SP-001: Add and edit course records.
- SP-002: Create a semester plan with credit totals.
- SP-003: Flag missing prerequisites when scheduling a course.
- SP-004: Show requirement completion status.

## Engineering Confidence Assessment

**Overall score:** 74/100

**Top risks:**

- Prerequisite rules may become complex if they include alternatives, co-requisites or department exceptions.
- Graduation progress depends on accurate requirement data.
- Manual setup may reduce adoption unless the first workflow is fast.

**Recommended actions:**

- Define the prerequisite rule format before implementation.
- Start with one degree plan template or a simple manual setup path.
- Keep every progress result traceable to the courses and requirements that produced it.
