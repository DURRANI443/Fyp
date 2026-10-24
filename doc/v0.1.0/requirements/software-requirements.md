# Software requirements specification

Version: v0.1.0  
Baseline date: 2026-10-24 (Asia/Karachi)  
Status: All requirements are **PLANNED**; verification is **NOT RUN**.

## Purpose and boundary

Specify a local, custom-built FYP system for customer support and ticket routing around a synthetic e-commerce store. The three application roles are customer, support staff, and administrator. OpenRouter is the only allowed external hosted model API. Live checkout, payment processing, and real refunds are excluded.

Requirement IDs remain stable across versions. The acceptance criteria below are project design criteria, not measured results or university-imposed thresholds. See [use cases](use-cases.md), [traceability](traceability-matrix.md), and [test strategy](../planning/testing-evaluation-strategy.md).

## Functional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| FR-001 | Authenticate users and enforce customer, support, and admin roles in the backend. | Unauthenticated access is rejected; each role can access permitted features only; modifying a client role value grants no privileges. |
| FR-002 | Provide a seeded demo catalog and owned-order history. | A customer sees their seeded orders and current product facts; a different customer's order identifier does not reveal its content. |
| FR-003 | Persist conversations and messages with their customer and ownership state. | Reloading a conversation preserves message order; another customer cannot read or append to it. |
| FR-004 | Detect supported intents and retain context needed for follow-up and mixed requests. | The system recognizes tracking, policy/product questions, cancellation, return, damage/missing-item complaints, billing inquiry, and explicit human requests; unresolved ambiguity prompts clarification or handoff. Mixed requests retain outstanding tasks. |
| FR-005 | Ingest and retrieve approved knowledge using local embeddings and PostgreSQL/pgvector. | Unapproved or withdrawn content is excluded; retrieved chunks retain document/version references; active-version changes are reproducible. |
| FR-006 | Generate policy answers from retrieved evidence with customer-visible source references. | Supported answers cite the approved document/version; absent or conflicting evidence leads to clarification or handoff; generation cannot invent order or payment state. |
| FR-007 | Retrieve order and shipment status from the application database after ownership checks. | An authenticated owner receives current seeded order facts; no-order and simulated-delivery-exception cases have defined responses; an order number alone never proves ownership. |
| FR-008 | Preview and execute eligible demo-order cancellations after customer confirmation. | The backend rechecks ownership and fulfillment state at execution; stale or expired confirmation is rejected; an eligible order changes state once and receives a recorded result. |
| FR-009 | Collect a return request for an owned order item using configured eligibility rules. | The system checks the delivery date, item, return window, and existing requests, records the reason, previews the request, and submits only after confirmation; exceptions route to staff without issuing a refund. |
| FR-010 | Route tickets to logistics, returns, billing, or general support using classifier output and explicit rules. | The ticket stores queue, priority, routing reason, and applicable rule version; delivery/cancellation conflicts and unknown intent have deterministic handling; no available staff leaves the ticket queued. |
| FR-011 | Provide explicit human handoff with a useful summary and pause assistant replies. | A human request or escalation creates/updates a ticket with request, verified facts, attempted actions, and unresolved needs; assistant replies pause in pending-human and human-owned states. |
| FR-012 | Provide staff queue access, authorized ownership, replies, and ticket resolution. | Staff can claim permitted queued tickets, see the conversation, reply, and resolve; concurrent claims have one winner; only explicit return-to-assistant resumes automation. |
| FR-013 | Allow administrators to manage knowledge approval, policy/routing configuration, and staff/team assignments. | Customer/support roles cannot change admin configuration; changes record actor, timestamp, version, and affected setting; active conversations recheck applicable action policy. |
| FR-014 | Integrate optional generation through a narrow backend-only OpenRouter adapter. | Only explicitly allowlisted routes with reviewed model licenses and validated zero-cost metadata can execute; missing credentials, timeout, quota, or ineligible route produces a safe fallback; no paid/provider fallback occurs. |
| FR-015 | Provide labeled offline/demo behavior and useful failure responses. | With generation disabled or unavailable, local order workflows and tickets still work; deterministic messages clearly disclose demo mode and are not logged as successful live model calls. |
| FR-016 | Record auditable actions and the provenance of generated answers. | Records link actor/conversation, action outcome, model ID when used, prompt/knowledge/rule versions, and latency; credentials and unnecessary customer details are absent. |
| FR-017 | Provide a reproducible routing and support-quality evaluation. | A versioned test set is evaluated against keyword, classifier-only, and hybrid routing; outputs include per-class metrics, macro-F1, confusion matrices, routing correctness, answer/workflow quality, latency, and failure cases. |

## Nonfunctional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| NFR-001 | Require no paid runtime service and use reviewed open-source application dependencies and models. | A dependency/model license inventory and pinned versions are present; the local reference deployment uses no paid subscription or proprietary container runtime; OpenRouter is documented as an external-service exception. |
| NFR-002 | Protect credentials, authentication material, and customer data. | Passwords are securely hashed; secrets are backend-only and ignored by Git; model requests contain only necessary redacted/synthetic data; cross-customer and role-denial tests pass. |
| NFR-003 | Prevent duplicate or partially applied material actions. | Repeated requests with the same scoped idempotency key return the same result; changed payloads are rejected; transactions prevent two cancellations/return submissions and inconsistent action/audit state. |
| NFR-004 | Bound generation resource use and degrade predictably. | Configuration limits request size, output tokens, timeout, concurrency, and retries; invalid or unavailable route metadata disables live generation; fallback remains usable. |
| NFR-005 | Keep setup and experiments reproducible. | A fresh environment follows validated setup steps, migrations, and seeds; tests run without an API key; datasets, seeds, models, prompts, and dependency versions are recorded. |
| NFR-006 | Provide accessible and understandable customer/staff interactions. | Core flows can be completed with keyboard navigation; controls have labels; confirmation and error states use text; ownership and demo/live state are visible. |
| NFR-007 | Measure responsiveness without treating free-model latency as guaranteed. | Local API, retrieval, generation, and end-to-end timings are reported separately with hardware and load. Proposed local-only target: p95 under 2 seconds for order lookup and ticket listing at five concurrent users on the documented test machine. |
| NFR-008 | Keep business decisions independent of model instructions. | Ownership, role checks, return/cancellation policy, queue rules, and tool permissions are enforced in backend code; prompt injection in a message or retrieved document cannot authorize an action. |
| NFR-009 | Support maintainable modules and meaningful automated verification. | API, persistence, retrieval, classification, routing, generation, and workflow code have clear boundaries; tests cover authorization, policy decisions, retries, and state transitions. |
| NFR-010 | Preserve SDLC history and evidence. | Versioned documents and diagrams have status/date/change log; captured baselines have a hash manifest; requirement-to-test links identify actual outcome or NOT RUN without inventing results. |

## Data and interface requirements

Planned entities include User, Team, Product, Order, OrderItem, ShipmentEvent, Conversation, Message, Ticket, ReturnRequest, ActionConfirmation, IdempotencyRecord, KnowledgeDocument, KnowledgeChunk, ConfigurationVersion, and AuditEvent. Diagram/entity details may refine this list without changing the required behavior.

- Use synthetic personal information and explicit demo identifiers.
- Keep timestamps in a consistent storage format; display user-facing project dates using Asia/Karachi.
- Store money values with currency and exact decimal semantics if shown; no real payment execution is exposed.
- Keep action confirmations tied to the authenticated customer, intended action, affected object, and expiry.
- Restrict idempotency keys to the authenticated action scope and compare request payloads before reuse.
- Use server-generated conversation/ticket references; do not accept identity asserted by a model response.
- Keep knowledge chunks traceable to approved source versions and distinguish document evidence from live order facts.

The browser calls the project API. The backend talks to PostgreSQL and, when explicitly enabled and eligible, OpenRouter. The browser never receives the model API key. Automated tests substitute deterministic model responses and route metadata.

## Initial policy decisions to implement and document

Cancellation eligibility, return-window duration, supported item exclusions, confirmation expiry, and queue priority thresholds must be explicit demo configuration before the corresponding workflow is implemented. No business-specific numeric policy is assumed in this baseline. Tests must cover the selected boundary values, and the UI must show the active policy.

