# Project agent instructions

Project: AI Customer Support and Intelligent Ticket Routing System for E-commerce

Initial baseline: 2026-10-24 (Asia/Karachi)

## Purpose

Build a custom, reproducible final-year project through a documented software development life cycle (SDLC). Implement a demo store, customer support chat, knowledge retrieval, order workflows, explainable ticket routing, and a staff dashboard. Develop in small, working increments and retain versioned requirements, diagrams, decisions, and verification evidence.

## User requirements

- Use open-source application code, libraries, database, and development tooling. No n8n or other hosted workflow platform.
- OpenRouter is the only permitted external hosted model API. Use explicitly selected free model routes only; never silently use a paid route.
- OpenRouter is an external service exception, not an open-source component. Free service access and open-source model licensing are different properties; verify both price and model license before selecting a route.
- Require no paid hosting, subscription, proprietary database, or proprietary desktop container runtime. Local execution on an existing computer is the reference deployment.
- The user has selected Supabase PostgreSQL, Vercel frontend hosting, and an Oracle Cloud backend for the optional hosted deployment. These managed services are authorized hosting exceptions; use their free allowances only and document quotas and setup requirements without promising perpetual availability. Application code remains open source.
- Keep every SDLC document, process description, and diagram under the singular `doc/` directory, grouped by version.
- The first deliverable is this instruction file and the documented technology/SDLC baseline. Do not describe planned application features as implemented.

## Selected technology direction

- Frontend: React, TypeScript, Vite, and ordinary CSS.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy, and Alembic.
- Database: SQLite is the portable v0.2.0 demo default; PostgreSQL is an optional SQLAlchemy deployment. The initial PostgreSQL/pgvector design remains the scaling direction. pgvector indexing is not implemented in v0.2.0; small-corpus local vectors are cached in process.
- AI: local sentence-transformer embeddings; a scikit-learn intent classifier; OpenRouter for grounded answer generation through a narrow HTTPX adapter.
- Routing: application-owned Python logic combining intent, conversation state, order facts, permissions, and team availability.
- Tests: pytest for backend/ML behavior; Vitest and React Testing Library for UI behavior; Playwright for end-to-end workflows.
- Documentation: Markdown and Mermaid source diagrams, with SVG exports when the renderer is available. Use Git for source history and named documentation baselines for milestone history.
- Dependency versions must be pinned and compatibility-tested when implementation begins; do not assume the newest runtime or package is compatible with the ML stack.

See `doc/v0.1.0/architecture/technology-stack.md` for rationale, license sources, deployment assumptions, and alternatives.

## Repository organization

```text
agent.md                 Canonical project instructions
AGENTS.md                Entry point to these instructions
README.md                Project overview and truthful implementation status
doc/                     Versioned SDLC evidence
  README.md              Version index and documentation conventions
  v0.1.0/                Initial requirements and architecture baseline
backend/                 Python API, services, migrations and tests
frontend/                Customer, staff and admin interface
data/                    Synthetic fixtures and labeled evaluation data
scripts/                 Project-local maintenance and verification tools
```

The v0.1.0 snapshot records the original plan. v0.2.0 records the working local MVP, implementation differences and actual verification. v0.2.1 records the shared-session fix. v0.3.0 adds a realistic demonstration catalog, simulated checkout, and the requested deployment configuration. The user requested a same-day, solo, English demo with default styling; completing and testing the core workflows takes priority over optional infrastructure.

## SDLC and versioning

1. Plan the increment and assign stable requirement IDs.
2. Update requirements, use cases, data model, architecture, and affected workflow diagrams.
3. Implement a small end-to-end slice.
4. Verify it with appropriate automated checks and representative manual scenarios.
5. Record actual commands, outcomes, limitations, and requirement-to-test links.
6. Record the release change log and capture a documentation baseline.

- Use `doc/vMAJOR.MINOR.PATCH/` with a README, status, date, and change log.
- A published baseline is immutable: subsequent changes belong in the next version. A draft can be edited until it is captured.
- Keep editable `.mmd` diagram sources and matching exports together. Mark planned architecture as planned.
- Do not invent test results, approval, metrics, completed milestones, or university requirements.
- Do not duplicate secrets, private customer data, or model API keys in documentation or diagrams.
- Update the root documentation index when adding a version. Preserve a manifest of baseline files and their hashes for integrity checks.

## Functional implementation rules

- One customer-facing assistant orchestrates bounded workflows. Keep identity, persistence, policy checks, routing, and generation in separate backend modules.
- Check authenticated customer ownership in backend code before every order lookup or action. Never trust a customer ID supplied by the language model.
- Enforce customer, support, and admin roles server-side.
- Read prices, inventory, order state, and return status from the application database, not from generated text or a stale document index.
- Retrieve approved knowledge before answering policy questions; retain document/version references.
- Keep return windows, cancellation eligibility, approval limits, and queue assignment rules in code/configuration, not only in prompts.
- Confirm material order changes, recheck current eligibility at execution, use transactions, and prevent duplicate actions on retries.
- Checkout is a simulation: label prices as demo prices, never collect real payment-card credentials, and never represent a simulated authorization or refund as a real transfer. Successful checkout must atomically reserve stock and create the customer's order; declines and failed transactions must not consume inventory.
- Provide explicit human handoff with a summary and reason. Pause assistant replies while a human owns a conversation.
- Unknown intent, missing evidence, API failure, and exhausted quota must lead to a useful fallback or ticket, not an invented answer.
- In offline/demo mode use labeled deterministic responses and real local workflows. Never present canned output as a successful live model call.

## OpenRouter integration rules

- Keep `OPENROUTER_API_KEY` exclusively on the backend in an ignored local environment file; provide only blank/example values in tracked configuration.
- Use a configurable, explicitly allowlisted model identifier and reviewed license. Avoid a general free-model router when it could select models outside the reviewed license list.
- Validate zero-cost route metadata before enabling live inference and fail closed if price/license eligibility cannot be established. Use provider price caps where supported.
- Do not enable paid fallback, web-search plugins, paid embeddings, automatic credit purchases, or another model provider.
- Bound request size, completion length, timeouts, concurrency, and retry count. Rate limits and model availability must be treated as changeable external constraints.
- Use synthetic demo customers and minimize/redact identifiers in model requests. Do not send secrets, payment credentials, or unnecessary customer details.
- Record model ID, prompt version, knowledge version, latency, and outcome without logging credentials.
- Tests run without network or a real API key by default. Make live API smoke checks an explicit, separate mode.

## Academic evaluation

- Compare keyword routing, a trained intent classifier, and the combined classifier-plus-rule router.
- Split data by complete conversation and group near-duplicate paraphrases to reduce leakage.
- Report per-class performance, macro-F1, a confusion matrix, routing correctness, grounded-answer quality, workflow success, handoff quality, and latency.
- Mark synthetic data as synthetic. Keep prompts, data versions, random seeds, and evaluation settings reproducible.
- Distinguish measured results from proposed acceptance targets. Document failure cases and model limitations.

## Engineering workflow

- Read these instructions and the latest documentation index before changes.
- Inspect existing files before editing; preserve unrelated user work.
- Prefer straightforward modules and a modular monolith before introducing additional services.
- Run only checks relevant to a change; add meaningful tests for authorization, policy decisions, routing, state transitions, and duplicate prevention.
- Keep configuration separate from code and publish exact setup instructions only after validating them.
- Report what exists, what was verified, and what remains. Never claim deployment or integration success without evidence.
