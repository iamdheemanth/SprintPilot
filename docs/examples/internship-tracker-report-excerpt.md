# Sample Report Excerpt: Internship Tracker

_This excerpt is a release-polish sample derived from SprintPilot Core v1 output. It is shortened for README and reviewer use._

## Original Product Idea

Build a student internship tracking platform that allows students to track applications, interview stages, offers, deadlines, recruiter contacts and application analytics.

## Product Definition

**Summary:** A student internship tracking platform that helps students manage applications, interview progress, offers, deadlines and recruiter contacts from one structured workspace.

**Primary users:**

- Student job seekers
- Career advisors

**Functional requirements:**

- FR-001: Students can create and update internship application records.
- FR-002: Students can track each application's stage, including applied, interview, offer, rejected and withdrawn.
- FR-003: Students can store deadlines, interview dates, recruiter contacts and follow-up notes for each application.
- FR-004: Students can review application progress without automating external submissions.

**User story sample:**

- US-001: As a student, I want to record an internship application with company, role, deadline and status, so that I can track every opportunity consistently.
  - Given a student has company and role details, when they create an application, then the application is saved with a default stage and deadline field.
  - Given required fields are missing, when the student saves the application, then the system identifies the missing fields.

## Architecture Plan

**Recommended architecture:** A modular local-first web application architecture with separate presentation, domain, workflow, persistence and reporting boundaries.

**System components:**

- Application Intake UI: Capture and edit internship application records.
- Application Service: Validate application fields, stage transitions, deadlines and recruiter contact links.
- Domain Models: Represent applications, stages, offers, deadlines, contacts, notes and next actions.
- Persistence Adapter: Store and retrieve structured application data through a replaceable boundary.
- Progress Summary Module: Generate simple counts and status summaries from existing records.

## Engineering Confidence Assessment

**Overall score:** 79/100

**Factor scores:**

- Requirement clarity: 100/100 - Requirements, stories, assumptions and acceptance criteria are clear.
- Architecture completeness: 100/100 - Components, stack categories, tradeoffs, assumptions and open questions are present.
- Dependency readiness: 50/100 - Open questions remain around permissions, reminders and summary expectations.
- Acceptance criteria quality: 100/100 - Story-level criteria are testable and reviewable.
- Technical ambiguity: 30/100 - Privacy and workflow decisions still affect implementation shape.
- Delivery risk: 70/100 - Core tracking is feasible, but analytics-style expectations could expand scope.

## Recommended Actions

- Prioritize application tracking and stage updates before advanced summaries.
- Define recruiter contact privacy expectations before implementation.
- Clarify reminder and deadline behavior before sprint start.
