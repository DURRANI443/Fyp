# System design

**Status:** Draft design for the documentation-only v0.1.0 baseline. No application modules, endpoints, integrations, or test results described here are implemented by this document.

**Date:** 2026-10-24 (Asia/Karachi)

**Project:** AI Customer Support and Intelligent Ticket Routing System for E-commerce

## 1. Scope and deployment boundary

The proposed system is a modular monolith with one customer-facing assistant, a synthetic store, and a staff support dashboard. The backend owns identity, order facts, policy checks, workflow state, and routing. A hosted language model supplies grounded wording through a restricted adapter; it does not own authorization or execute arbitrary actions.

The first MVP supports product and policy questions, synthetic order tracking, eligible synthetic order cancellation, return-request intake, human handoff, and explainable staff assignment. Cancellation requires customer confirmation and a transactional eligibility recheck before changing the local demo order state once. A cancellation receipt reports that committed synthetic order change. A return-request receipt reports only that the request was recorded; it does not mean a parcel was returned or money refunded. There are no real payments, refunds, carrier integrations, or live-store writes in the first MVP. All order changes remain explicitly synthetic and audited.

Local execution on an existing computer is the reference deployment. Native frontend, Python backend, and PostgreSQL processes are sufficient. An optional Podman configuration may be added after native setup is validated. Docker Desktop, paid hosting, Redis, background task queues, and separate microservices are not prerequisites.

See [technology-stack.md](technology-stack.md) for technology and license evidence and [decisions.md](decisions.md) for architectural decisions. These design choices are proposed baseline decisions, not a record of user approval.

## 2. Components

| Component | Responsibility | Explicit boundary |
| --- | --- | --- |
| React, TypeScript, Vite UI | Customer chat, request review, order views, staff queues, and admin knowledge management | Does not decide permissions, ownership, eligibility, or prices |
| FastAPI API and Pydantic contracts | Request validation, authentication, authorization, typed responses, and error handling | Does not expose database objects or provider credentials directly |
| Python application modules | Conversation orchestration, policy evaluation, routing, request transactions, and audit | Keep business decisions independent of language-model text |
| SQLAlchemy and Alembic | Persistence access and versioned schema migrations | Application services control transaction boundaries |
| PostgreSQL and pgvector | Structured operational data, approved knowledge chunks, and local vector search | Every query applies the appropriate customer or staff scope |
| Local ML components | Sentence-transformer embeddings and scikit-learn intent classification | No hosted embedding API or model-provider access is required |
| HTTPX OpenRouter adapter | Bounded generation through an explicitly reviewed free route | Only external hosted model API; no paid fallback or arbitrary tool execution |

The frontend calls the backend; it never calls OpenRouter or PostgreSQL. Native development can use separate frontend and API ports with an exact origin allowlist. A packaged local deployment should prefer one browser origin through a proxy or backend-served frontend assets. Hosting and packaging details remain subject to implementation validation.

## 3. Backend modules and contracts

These names describe logical Python modules, not files already present in the repository.

| Module | Owns | Main proposed contract |
| --- | --- | --- |
| `identity` | Users, password verification, server-side sessions, roles, CSRF, authorization scopes | `authenticate(session) -> ActorContext`; `require_permission(actor, operation, resource)` |
| `catalog` | Synthetic products, prices, inventory, and product attributes | `get_product(product_id) -> ProductSnapshot` |
| `orders` | Customer-scoped synthetic order reads and order item references | `get_owned_order(actor, order_id) -> OrderSnapshot` |
| `conversations` | Messages, customer ownership, conversation mode, and staff ownership | `append_message(actor, conversation_id, message) -> MessageReceipt` |
| `intent` | Versioned TF-IDF classifier loading, intent predictions, and evaluation metadata | `classify(text, context) -> IntentPrediction` |
| `knowledge` | Approved document versions, chunking, local embeddings, and filtered retrieval | `retrieve(query, scope) -> EvidenceBundle` |
| `policies` | Return windows, request eligibility, required fields, and workflow constraints | `evaluate(action, actor, facts, policy_version) -> PolicyDecision` |
| `workflows` | Draft action proposals, confirmations, synthetic cancellation, return-request transitions, and idempotent writes | `confirm_proposal(actor, proposal_id, idempotency_key) -> WorkflowResult` |
| `routing` | Intent-to-team rules, priority factors, language/availability checks, and assignments | `route(context, facts, candidates) -> RoutingDecision` |
| `generation` | Prompt construction, reviewed route selection, HTTPX adapter, and deterministic fallback | `generate(answer_context) -> GenerationResult` |
| `tickets` | Ticket lifecycle, handoff summaries, staff claim/reassignment, and unresolved reasons | `handoff(actor, conversation_id, reason) -> TicketReceipt` |
| `audit` | Immutable business-event records and redacted operational measurements | `record(event, transaction)` for business changes; separate operational telemetry |

Use typed application-level objects rather than passing unrestricted model-generated dictionaries between modules. Important proposed fields include:

- `ActorContext`: server-derived user ID, current role, session reference, and resource scope. It is never constructed from a model-provided customer ID.
- `IntentPrediction`: one or more candidate intents, score, ambiguity flag, classifier artifact version, and fallback provenance. A raw model score is not automatically a calibrated probability.
- `EvidenceBundle`: approved chunk IDs, document/version references, retrieved text, similarity results, and retrieval status.
- `PolicyDecision`: allowed/denied/needs-information result, rule IDs, required inputs, rationale code, policy version, and facts used.
- `RoutingDecision`: selected team, optional staff member, priority, reason codes, routing-rule version, and decision factors.
- `WorkflowResult`: action kind, order ID, return-request ID when applicable, committed state, whether a retry reused an existing result, and a customer-safe description distinguishing a synthetic cancellation from return-request creation.
- `GenerationResult`: text, evidence references, live-model/deterministic-fallback mode, model ID when used, prompt version, latency, and outcome code.

HTTP-facing contracts expose only the fields required by that user role. Internal scores, staff-only notes, private policy administration details, and other customers' records are excluded from customer responses.

## 4. Message processing and routing order

1. Validate the request, authenticate the session, check CSRF where applicable, and authorize access to the conversation. Store the customer message with an ID that can prevent duplicate submission.
2. Inspect conversation mode. In `handoff_pending` or `human_owned`, record the message for the queued ticket or assigned staff member and suppress automated assistant replies. An explicit request for a human immediately enters the handoff path without requiring an intent threshold. A one-time deterministic handoff receipt may acknowledge the transition; subsequent customer messages do not restart automated answers while either state is active.
3. Determine whether this is a new request or a continuation of a pending workflow. Recover server-held context; do not treat instructions inside a customer message as authority to change roles, policy, or workflow state.
4. Run the local classifier and retain multiple intent candidates where needed. Combine its output with conversation state and deterministic rules. For ambiguous intent, request a focused clarification. Thresholds must be tuned on held-out validation data rather than asserted as accurate in advance.
5. Fetch required structured facts. Every order access checks authenticated ownership in backend code. Missing order information triggers a clarification; an inaccessible order does not reveal whether it belongs to another customer.
6. Apply explicit policy and workflow rules to current facts. A multi-intent request such as "My delivery is late; cancel it" must check fulfillment before presenting an eligible synthetic cancellation option. Preserve each unresolved intent in the ticket summary.
7. Select an answer, action proposal, or handoff. Policy questions require approved evidence; catalog/order facts use database snapshots. A material action is offered as a structured proposal for confirmation, not inferred from an unconfirmed generated sentence.
8. Produce wording from the authorized answer context. Use generation only when the configured route is eligible and available. Use a deterministic response or ticket when evidence or generation is unavailable. Validate the response format and referenced evidence; this does not by itself prove semantic correctness, which remains an evaluation requirement.
9. Persist the response mode, evidence/version references, decision reasons, and outcome. Recheck conversation mode before emitting an automated reply; suppress an in-flight model response if `handoff_pending` or `human_owned` has been entered since generation started.

The local classifier predicts intent. The application router makes workflow and assignment decisions from that intent plus facts, permissions, state, and rules. The hosted generator phrases an answer using permitted context. These are separate responsibilities and should be evaluated separately.

## 5. Explainable staff assignment

Assignment proceeds in a fixed, inspectable order:

1. Map unresolved intent to an eligible team using versioned rules: delivery and fulfillment-related cancellation exceptions to logistics, return requests to returns, payment questions to billing, and unresolved general questions to general support. Successful self-service cancellation does not itself require a staff ticket; unresolved mixed requests still do.
2. Derive priority from documented factors such as a demonstrated approaching request cutoff or repeated unresolved contacts. Customer tone alone does not establish urgency or a factual delivery exception.
3. Keep an existing eligible owner where continuity is useful. Otherwise filter staff by role, team membership, availability, and supported language when recorded.
4. Use open assigned ticket count as a simple load measure, with a stable tie-breaker. Recheck candidate availability and workload inside the assignment transaction; initially serialize competing assignments within a team using a database lock.
5. If nobody is eligible, leave the ticket unassigned in the team queue. Do not invent availability or drop the ticket. Staff can claim or reassign tickets within their permissions, with an audit record.

A staff-visible explanation might read: "Logistics queue: shipment is overdue according to the local order record; the previous owner is unavailable; no eligible agent is currently available." Store the factual inputs and rule identifiers behind this explanation. Customers receive only an appropriate summary, not private staffing information.

For requests involving multiple teams, create one primary ticket with all unresolved intents and an explicit secondary-team note in the MVP. Separate linked subtickets are a later extension; automatic duplicate ticket creation is not required.

## 6. Data ownership, identity, and sessions

The proposed roles are `customer`, `support`, and `admin`. Role checks run server-side for every operation; hidden UI controls are not access control.

| Data | Customer access | Support access | Admin access |
| --- | --- | --- | --- |
| Catalog and approved public knowledge | Read | Read | Manage with version history |
| Orders and request status | Own records only | Records needed for authorized support work | Authorized administration of synthetic data |
| Conversations and messages | Own conversations only | Team/assignment-scoped conversations | Authorized support administration |
| Tickets and staff notes | Customer-safe status only | Eligible team tickets and permitted assignments | Team/rule administration |
| Sessions, credential hashes, model key | Own session lifecycle only; never secret values | No secret read access | Configuration capabilities do not expose stored secrets through the UI |
| Audit and evaluation records | No general browsing access | Operational records needed for assigned work | Restricted audit/evaluation access |

Use seeded synthetic accounts initially; self-service signup, password recovery, and email delivery are outside the first slice. Passwords must be hashed using a reviewed password-hashing implementation selected during implementation. Never store plaintext passwords.

Sessions use unpredictable opaque tokens in cookies, with token hashes and expiry/revocation state held server-side. Rotate sessions on login and privilege changes, expire inactive sessions, and revoke them on logout. Resolve current privileges from backend-controlled state so role removal takes effect without trusting a stale client claim.

Cookies should be `HttpOnly`, use an appropriate `SameSite` policy, and be `Secure` whenever HTTPS is used. Any HTTP-only development exception is restricted to the documented loopback setup, not a production configuration. Do not store authentication tokens in browser local storage. Use a session-bound CSRF token in a request header for cookie-authenticated unsafe requests, validate request origin, and protect the login flow from cross-origin submission. Development CORS must allow only the selected frontend origin, never wildcard credentialed access.

Do not log session tokens, credentials, the OpenRouter API key, or raw authorization headers. Return customer-safe errors without exposing another customer's order existence. Rate and size limits apply to login, chat, and generation independently of role checks.

## 7. Workflow confirmation, consistency, and duplicate prevention

Initial material writes are eligible synthetic order cancellation and creation or update of a return request. A proposal must identify its action kind (`cancel_order` or `create_return_request`), owned order and relevant items, quantity where applicable, reason, current eligibility, intended effect, and an expiry. A customer confirms that exact proposal through a structured UI action. Cancelling an eligible synthetic order changes its local state to `cancelled`; creating a return request records a separate request without claiming a refund or completed return.

At confirmation, the backend must:

1. Authenticate again, authorize ownership, verify CSRF, and validate a client idempotency key scoped to actor and operation.
2. Start a database transaction and claim the idempotency record under a uniqueness constraint. Bind it to a hash of the validated request; reusing the key with different input returns a conflict.
3. Lock the relevant proposal/order/request rows, re-read current order and item state, and re-evaluate policy. Check proposal expiry, prior consumption, cancellation eligibility, overlapping requests, quantity limits, and current authorization. A shipped or otherwise ineligible order cannot be cancelled because an earlier preview allowed it. Never execute solely from the earlier preview.
4. If the confirmed proposal is no longer valid, return a specific conflict or a new proposal for confirmation. Changed material terms must not be accepted silently.
5. For cancellation, transition the eligible synthetic order to `cancelled` once; for a return, insert or transition the return request. Write the audit event, consume the proposal, and persist the idempotent result in the same transaction.
6. Commit before reporting success. A retry returns the stored committed result rather than cancelling again or creating another return request. Transaction rollback must not leave an apparent successful action.

Database uniqueness constraints, allowed-transition checks, and order locks protect against duplicate cancellation even when different idempotency keys are submitted. An already-cancelled order cannot produce a second cancellation transition or success audit event. Locked overlap checks also protect against two keys creating the same active return request. For returns, check the requested item quantities against existing active requests under the same order lock. State transitions should use a version counter or equivalent conflict check as well as allowed-transition rules.

Staff assignment, claim, and resolution transitions also require concurrency checks and audit records. Generation calls run outside database transactions and cannot make a committed workflow depend on a successful external text response. If generation fails after a commit, return a deterministic cancellation receipt with the synthetic order ID and committed `cancelled` state, or a return-request receipt with the request ID and committed request status, according to the action performed.

## 8. Knowledge, model, and policy provenance

Approved knowledge flows through an admin-controlled ingestion operation: validate source and visibility, create a document version, chunk locally, embed locally, and activate a complete index version. Customer messages and uploaded unapproved content never become authoritative policy automatically.

Each chunk records document ID, document version, chunk ID, approval state, visibility, embedding model identifier/revision, and embedding configuration. An embedding change requires a deliberate re-index; incompatible vectors must not be mixed. Retrieval filters out unapproved, inactive, or unauthorized content before answering.

Version and retain the following references for reproducibility:

| Artifact | Record with decisions or evaluation runs |
| --- | --- |
| Store policy | Policy version, effective version at proposal and execution, rule IDs |
| Routing configuration | Routing-rule version and decision inputs |
| Knowledge | Active index version and exact cited document/chunk versions |
| Intent classifier | Artifact hash/version, label schema, training-data version, split/seed settings, preprocessing configuration |
| Local embeddings | Model identifier/revision, license review reference, vector dimension, normalization/chunking configuration |
| Hosted generation | Configured model/route ID, reviewed license reference, price-validation time/result, prompt version, generation settings |
| Application and schema | Source revision where available and Alembic migration revision |

Hosted providers can change model implementations or availability. Recording configuration improves traceability but does not guarantee bit-for-bit reproducibility of hosted answers. Store only appropriately minimized evaluation transcripts and actual outcomes, not claims of reproducibility that cannot be verified.

## 9. Source boundaries and external model use

- **Trusted instructions:** Application code, reviewed workflow configuration, approved policy versions, and authenticated role information determine permitted behavior.
- **Authoritative facts:** PostgreSQL holds synthetic prices, inventory, order state, request state, and staffing availability. Generated text and retrieved prose cannot overwrite these facts.
- **Approved evidence:** Versioned public knowledge provides answer content within its scope. Retrieved text is data, not executable instructions; approval does not make embedded instructions authoritative.
- **Untrusted input:** Customer text, document contents, and model output are validated and handled as data. They cannot supply an actor identity, bypass policy, choose arbitrary network URLs, or call arbitrary backend functions.
- **External boundary:** Only the backend HTTPX adapter contacts OpenRouter for hosted model inference. Send the minimum synthetic question, relevant approved excerpts, and redacted structured facts. Do not send full order records, secrets, payment credentials, or unrelated conversations.

The first adapter is answer-generation-only. It accepts a prepared `AnswerContext` and returns a validated `GenerationResult`; it does not expose generic SQL, HTTP, filesystem, or order mutation tools to the model. Customer-visible citations must refer to retrieved approved evidence, not model-invented document identifiers.

The candidate configured in the example is `google/gemma-4-31b-it:free`; [technology-stack.md](technology-stack.md) records the catalog and license review. It remains subject to task evaluation and fresh route checks; the live integration is not configured or verified by this baseline. Configuration must explicitly allowlist the reviewed model identifier. Validate current zero-cost route metadata before enabling live inference and revalidate on a bounded schedule and configuration change. Fail closed when price/license eligibility cannot be established; use provider price caps where supported and disable paid fallbacks and add-ons. There is no general free-model router that can choose outside the reviewed allowlist.

Bound input size, output tokens, concurrency, timeout, and retries. Use only short bounded retries for transient failures; exhausted rate limits or quota must reach a fallback promptly. Store the key exclusively in an ignored backend environment file and keep secret values blank in tracked example configuration. Nonsecret example settings may identify the reviewed candidate model; default `LLM_MODE` to `offline` until local setup and eligibility checks are complete.

## 10. Failure and fallback behavior

| Condition | Planned response |
| --- | --- |
| Unknown or conflicting intent | Ask one focused clarification; offer or create a handoff when unresolved |
| Classifier missing or unavailable | Use a labeled conservative keyword fallback and clarification; disable unverified automated intent-dependent decisions |
| Customer requests a human | Create/reuse a ticket, summarize verified context, enter `handoff_pending`, and pause automated answers |
| Knowledge missing, stale, or contradictory | State the missing information and route the question; do not invent policy |
| Order missing or inaccessible | Ask for an accessible reference without exposing other customers' data |
| Order or policy changes during confirmation | Reject the stale proposal and present current eligible options |
| OpenRouter unavailable, quota exhausted, or route review fails | Use deterministic local facts/templates and real local workflows; hand off questions requiring unavailable generation |
| Database unavailable | Do not claim a lookup, ticket, synthetic cancellation, or return request succeeded; report a retryable failure |
| No eligible staff member | Keep the ticket visible in its team queue with an unassigned reason |
| Handoff starts or a human claims the conversation during generation | Discard/suppress the pending assistant reply and retain `handoff_pending` or `human_owned` |

Offline/demo mode must visibly identify deterministic responses. A successful local workflow is real within the synthetic database; it is not a successful hosted model call or a live commerce transaction. Operational records distinguish live generation, offline mode, fallback, denied workflow, and failed persistence.

## 11. Conceptual API inventory

This inventory is a draft contract outline, not an implementation, tested API, or final OpenAPI specification. All resource routes require the authorization scopes above. State-changing routes additionally require the relevant CSRF and concurrency/idempotency protections.

| Method and route | Purpose | Principal scope |
| --- | --- | --- |
| `POST /api/auth/login` | Start a server-side session for a seeded account | Login protections |
| `POST /api/auth/logout` | Revoke current session | Authenticated actor |
| `GET /api/auth/me` | Return safe current identity and role | Authenticated actor |
| `GET /api/auth/csrf` | Obtain the current session-bound CSRF value | Authenticated actor |
| `GET /api/products` | Search/read synthetic catalog | Customer/support/admin |
| `GET /api/orders` | List scoped order summaries | Customer's own records; authorized staff scope |
| `GET /api/orders/{order_id}` | Read a scoped order snapshot | Ownership or permitted staff scope |
| `POST /api/conversations` | Create a customer-owned conversation | Customer |
| `GET /api/conversations/{conversation_id}` | Read scoped transcript and mode | Owner or permitted staff |
| `POST /api/conversations/{conversation_id}/messages` | Submit a customer message | Customer owner |
| `POST /api/conversations/{conversation_id}/handoff` | Request a human and create/reuse ticket | Customer owner or permitted staff |
| `POST /api/action-proposals` | Preview an eligible synthetic cancellation or return-request creation | Customer with owned order |
| `POST /api/action-proposals/{proposal_id}/confirm` | Confirm the exact action proposal and return its distinct committed receipt | Customer owner; idempotent |
| `GET /api/requests/{request_id}` | Read request status and customer-safe history | Owner or permitted staff |
| `GET /api/staff/tickets` | Read eligible team queues | Support/admin |
| `POST /api/staff/tickets/{ticket_id}/claim` | Claim an available ticket atomically | Eligible support/admin |
| `POST /api/staff/tickets/{ticket_id}/assign` | Assign/reassign within authorized team scope | Authorized support/admin |
| `POST /api/staff/tickets/{ticket_id}/messages` | Add staff reply or permitted internal note | Assigned/authorized support/admin |
| `POST /api/staff/tickets/{ticket_id}/resolve` | Resolve with recorded outcome | Assigned/authorized support/admin |
| `POST /api/staff/requests/{request_id}/status` | Record a permitted request review transition | Authorized support/admin |
| `POST /api/admin/knowledge/versions` | Add a draft approved-source candidate | Admin |
| `POST /api/admin/knowledge/versions/{version_id}/activate` | Approve and activate a complete local index version | Admin |
| `GET /api/admin/audit` | Inspect restricted decision and workflow evidence | Admin |

Use a consistent error envelope with a stable code, safe message, correlation ID, and optional field errors. Pagination, payload limits, route naming, DTO schemas, and exact status codes must be finalized and tested during implementation. Cancellation changes only the synthetic order database. Neither that change, return-request status changes, nor ticket resolution implies that a real refund or shipment action occurred.

## 12. Training, generation, and verification

The academic ML work is local intent-classifier training and evaluation. Train a TF-IDF feature pipeline and scikit-learn classifier from labeled synthetic support conversations. Split by complete conversation and group near-duplicate paraphrases across splits. Keep a held-out test set separate from threshold tuning. Compare a keyword baseline, classifier-only routing, and classifier-plus-rule routing using the same scenarios and documented conditions.

Sentence-transformer embedding weights are pretrained and run locally; initial scope does not require training that model. The OpenRouter answer model is also pretrained and hosted; calling it is inference, not training a new language model. Initial scope does not require fine-tuning either model.

Planned checks use pytest for policy, ownership, routing, state transitions, duplicate prevention, and ML evaluation; Vitest with React Testing Library for UI behavior; and Playwright for representative customer-to-staff workflows. Default tests use stubbed generation and no real API key. A live OpenRouter smoke check is a separate explicit mode after route eligibility is verified.

Measure per-class intent performance, macro-F1, confusion matrices, routing correctness, grounded-answer quality, workflow success, handoff completeness, and latency. Evaluate deterministic workflow behavior separately from hosted answer wording. Include negative cases such as another customer's order ID, stale confirmations, concurrent retries, unavailable staff, prompt injection, missing knowledge, and generation failure after a successful database commit.

No measurements or pass claims are available in this documentation-only baseline. Acceptance targets and recorded execution evidence belong in the versioned requirements and verification documents.
