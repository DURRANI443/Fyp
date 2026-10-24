# Incremental SDLC plan

Version: v0.1.0  
Baseline date: 2026-10-24 (Asia/Karachi)  
Status: Planning only. No application implementation, integration, or test execution is claimed.

## Development process

Use an incremental SDLC with short, reviewable vertical slices. Each increment repeats requirements review, design, implementation, verification, and baseline capture. Milestones depend on exit evidence rather than invented calendar deadlines.

1. Choose a slice from the backlog and identify its requirement IDs and acceptance criteria.
2. Update the relevant design, data model, workflow, and decision records.
3. Implement the slice across interface, API, persistence, and permissions as needed.
4. Run meaningful unit, integration, and end-to-end checks for the changed behavior.
5. Record commands, environment, actual outcomes, unresolved defects, and requirement links.
6. Update the change log and documentation index; capture the next immutable version baseline.

## Milestones and backlog increments

| Version | Backlog ID | Planned deliverable | Exit evidence |
| --- | --- | --- | --- |
| v0.1.0 | INC-01 | Canonical agent instructions; scope; SRS; use cases; architecture; diagrams; evaluation plan | Documents cross-reference requirements and distinguish plans from verified results. |
| v0.2.0 | INC-02 | React/FastAPI project foundation; PostgreSQL migrations; configuration; local setup; synthetic seed framework | Frontend reaches API; database migration and seed run locally; secrets remain untracked; dependency/license inventory recorded. |
| v0.3.0 | INC-03 | Customer/support/admin authentication and roles; demo catalog; owned-order access; persisted conversation model | Ownership and role-denial checks pass; fresh setup creates repeatable sample data. |
| v0.4.0 | INC-04 | Approved-knowledge ingestion and retrieval; classifier; routing baselines; bounded OpenRouter adapter and fallback | Retrieval and routing tests pass; route eligibility and quota failures are tested without paid calls; model/data versions recorded. |
| v0.5.0 | INC-05 | Cancellation and return workflows; confirmation and retry safety; staff dashboard; ticket ownership and resolution | Customer-to-staff scenarios pass, including changed eligibility, retries, and paused assistant behavior. |
| v0.6.0 | INC-06 | Evaluation dataset freeze; comparative experiment; end-to-end validation; release candidate | Actual results, confusion matrices, failure analysis, setup verification, and remaining defects are recorded. |
| v1.0.0 | INC-07 | Final demonstration, reproducibility package, report, and final documentation baseline | In-scope acceptance evidence is linked; final limitations and licenses are disclosed; final baseline manifest is checked. |

All application milestones are **PLANNED**. INC-01 is the documentation work associated with this baseline; the presence of the plan is not evidence that later milestones are complete.

## Suggested vertical slices

- Foundation: start the API and UI, connect the database, and show seeded products.
- Authorized support: log in, view an owned order, and save a conversation.
- Grounded help: retrieve an approved policy, show source references, and fall back safely.
- Routing: classify a request, apply a rule, and show the assigned queue and reason.
- Controlled action: preview an eligible cancellation, confirm, execute once, and show resulting state.
- Human support: escalate a conversation, take ownership, reply, and close or explicitly return it to the assistant.

## Change control

Record a scope or design change in the next draft baseline with its reason, affected requirement IDs, compatibility impact, and verification work. Retain requirement IDs across versions. Mark removed requirements as retired rather than reusing their identifiers. Add a new ID when a new independently testable behavior appears.

A captured baseline is immutable; corrections belong in a later version. Draft files may change until capture. Each baseline includes a README/status, change log, and file manifest with hashes under the repository's documentation conventions. Link to prior decisions rather than silently rewriting their history.

## Definition of done for an application increment

- Acceptance criteria for the increment are implemented and linked to evidence.
- Role, ownership, state-transition, and failure paths relevant to the slice are checked.
- Tests use synthetic data and run without a live model API by default.
- User-visible demo behavior and unavailable integrations are labeled honestly.
- Dependencies, configuration, migration steps, and known defects are documented.
- Documentation and diagrams reflect the actual delivered behavior, with remaining work marked planned.

