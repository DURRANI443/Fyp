# Implementation scope and design

Version: v0.2.0  
Date: 2026-10-24, Asia/Karachi  
Predecessor: [v0.1.0 requirements](../v0.1.0/requirements/software-requirements.md)

This increment implements a local, English-language demonstration of the Northstar store and its support workflows. The user is working alone and requested a usable solution today, a default theme, free/open-source application components, and an OpenRouter key to be supplied later. Several originally planned increments are consolidated into this MVP. The application is not a deployed commercial support service.

## Delivered components

| Component | Implemented behavior | Source |
| --- | --- | --- |
| Customer workspace | Demo-account sign-in, seeded catalog, owned-order history/details, chat, action previews and explicit confirmations | [Customer UI](../../frontend/src/customer.tsx), [application shell](../../frontend/src/App.tsx) |
| Staff workspace | Team-filtered queue, claim, conversation/order inspection, replies, return approval/rejection, resolution and explicit return to assistant | [Staff UI](../../frontend/src/staff.tsx), [support routes](../../backend/app/routes/support.py) |
| Administration | Knowledge versions and approval, staff team/availability changes, audit records and aggregate counts | [Core API](../../backend/app/routes/core.py) |
| Authentication | Argon2 password hashing, random HTTP-only cookie sessions, stored token hashes, CSRF protection on authenticated writes, backend role/ownership checks | [Authentication](../../backend/app/auth.py) |
| Persistence | SQLAlchemy models, initial Alembic migration, synthetic seed data, transaction-protected workflow state | [Models](../../backend/app/models.py), [migration](../../backend/migrations/versions/e47fda0400ac_initial_schema.py), [seed](../../backend/app/seed.py) |
| Intent detection | Locally trained TF-IDF/logistic-regression classifier with separately identifiable rule precedence, simple negation guard and mixed-intent output | [Intent engine](../../backend/app/ai/intent.py) |
| Knowledge retrieval | Highest approved version per document key, document/version citations, local CPU embeddings when the reviewed cache is available, TF-IDF fallback otherwise | [Retrieval](../../backend/app/ai/retrieval.py) |
| Optional generation | Backend-only OpenRouter adapter, reviewed route allowlist, current metadata checks and zero-price caps, no provider fallback or model tools, bounded requests and redaction | [Adapter](../../backend/app/ai/openrouter.py) |
| Evaluation | Versioned synthetic intent/retrieval cases and a reproducible script comparing keyword, classifier-only and hybrid results | [Evaluation script](../../backend/scripts/evaluate.py), [intent dataset](../../data/intents/v1/dataset.json), [retrieval cases](../../data/retrieval/v1/cases.json) |

The UI distinguishes local and generated messages. Offline mode does not call a hosted model. Approved policy excerpts, actual local order data and staff routing remain usable without a key. Product answers use the catalog database, not generated prices or stock figures.

## Selected deployment and scope adjustments

The reference startup uses **SQLite with WAL** so the solo student can run the application without installing a database server. The optional relational PostgreSQL path was separately verified using native PostgreSQL 17.11: the initial migration and synthetic seed passed, followed by all 64 backend cases against isolated test schemas. The reported suite duration was 145.68 seconds. [Verification](verification.md) records the commands and environment; this is independent PostgreSQL evidence rather than an inference from SQLite tests.

The original PostgreSQL/pgvector direction is retained as a later scale-up task. **pgvector storage/indexing is not implemented in this increment.** Retrieval computes similarities over the small approved document set in process. Cached sentence-transformer vectors are held in memory; TF-IDF is the explicit fallback when the local model or optional dependencies are unavailable. Loading the embedding model does not silently download files or run remote model code. The actual tested retrieval mode is reported in the verification record.

The frontend uses React, TypeScript, Vite and CSS. The backend is a FastAPI modular monolith; it owns identity, policy, routing and actions. There is no n8n, payment service, hosted workflow engine, required container runtime or browser-held model secret. OpenRouter is an optional hosted-service exception, not an open-source application component. Model-route availability and zero-cost eligibility are revalidated at inference time; a configured route is not a guarantee of service availability.

## Order and return policies

| Decision | Current behavior |
| --- | --- |
| Cancellation | Only an owned order whose status is `processing` may be cancelled |
| Return window | Delivered orders within 30 days; the value is backend configuration |
| Return quantity | Must belong to the selected order and cannot exceed purchased quantity less active requested/approved returns |
| Return reason | Required before submitting a return request |
| Confirmation | Preview first; proposal expires after 10 minutes by default |
| Revalidation | Recheck authenticated ownership, current order version, policy version, eligibility and expiry at confirmation |
| Idempotency | Unique customer/key pair, fingerprint bound to proposal; conflicting reuse is rejected |
| Atomicity | Transactional audit/result write, order-version compare-and-set, unique constraints; PostgreSQL row locks supplement these safeguards |
| Return outcome | Create a `requested` return for staff review; no real refund or replacement is executed |
| Staff review | Returns-team staff or administrators may approve/reject a pending return; the review decision is final in this MVP |

Cancellation changes synthetic order state once. Returns increment the order version and create a reviewable request. Confirmed returns create or use a conversation with a returns ticket so the staff workspace can discover them. Rejected quantities become available for a later new request; approved/requested quantities remain reserved. No payment credentials are collected.

## Conversation and routing behavior

Conversation modes are `assistant`, `handoff_pending`, `human_owned` and `closed`. A human request, unsupported question or applicable workflow exception queues a ticket. The assistant pauses immediately in pending and owned modes, while the customer can still send messages to staff. A staff member must explicitly claim a ticket before representing an active human connection. Only resolution with `return_to_assistant=true` resumes automated replies.

Messages are deduplicated by client message ID within their conversation, with a conflicting-content check. The backend commits the customer turn before awaiting a hosted answer. Before publishing an answer, it atomically checks that the conversation is still in assistant mode. A handoff during an in-flight model request therefore suppresses the late automated reply.

| Situation | Queue/behavior |
| --- | --- |
| Recorded shipment delay or delivery exception | Logistics; high priority is based on the stored exception |
| Shipped cancellation, especially a late/cancel mixed request | Logistics review; no automatic cancellation |
| Confirmed return or damaged-item review | Returns |
| Payment/refund-status inquiry | Billing; no payment action |
| Uncertain intent, absent approved evidence or generic human request | General support unless known conversation context identifies a team |
| No claimant yet | Remain queued and show that state; no availability or response-time promise |

Conversation context retains selected order, pending workflow and return item/reason clarification. The implementation handles the demonstrated late/cancel combination, but it does not implement a general planner or durable queue for every task in an arbitrary multi-intent request. Routing records a textual reason and priority; a separately versioned routing-rules table is deferred.

## Schema differences from the initial design

The actual model has 13 tables: users, sessions, products, orders, order_items, conversations, messages, tickets, proposals, return_requests, idempotency_records, knowledge_documents and audit_events. [The data diagram](diagrams/data-model.svg) shows their key fields and relationships.

Teams are a validated JSON list on a user and a controlled ticket value, not a separate `Team` table. Shipping status/tracking are order fields; the displayed timeline is derived, not a `ShipmentEvent` log. `Proposal` is the implemented action-confirmation entity. Knowledge versions are document records, without a persisted chunk/vector table. Policy versions are bound to proposals; there is no general configuration-history entity. Money is stored as integer minor units with an explicit currency.

## Deferred work and limitations

- Production deployment, real checkout, actual shipping/carrier integrations, refunds, replacements, WhatsApp/email, voice, file/photo uploads and multilingual chat are outside this increment.
- PostgreSQL/pgvector indexing, document chunking and large-corpus retrieval are deferred; this is a small synthetic knowledge set.
- A runtime policy/routing editor, durable configuration history, general multi-task orchestration and automatic skill/availability-based assignment are deferred.
- Audit events and message metadata exist. The generator emits model/prompt/source/latency metadata to application logging, but a durable, conversation-linked generation-provenance table and structured-log retention pipeline are not implemented.
- Synthetic classifier results are an academic baseline, not evidence of accuracy on real customer traffic. Complete human-rated grounding/handoff quality, load testing and a comprehensive keyboard/screen-reader audit remain separate verification tasks.
- A real OpenRouter inference requires the user's locally configured key and an eligible available route. Mock-provider tests do not constitute a successful live inference.

See [requirements traceability](requirements-traceability.md) for partial baseline criteria and [verification](verification.md) for executed checks and remaining gaps.
