# Architecture decision records

**Status:** Draft architecture decisions for the initial documentation-only baseline. These records describe the selected implementation direction and its tradeoffs; they do not claim user approval, implemented components, completed verification, or deployment.

**Date for all records:** 2026-10-24 (Asia/Karachi)

Exact dependency versions and model revisions remain to be pinned and compatibility-tested before implementation. Runtime targets and candidate embedding/generation models are recorded in [technology-stack.md](technology-stack.md), with license evidence and deployment qualifications. The hosted integration remains unconfigured and requires task evaluation and fresh route checks. See [system-design.md](system-design.md) for the proposed contracts and processing order.

## ADR-001: Use a modular monolith

**Status:** Draft selected direction.

**Context:** This final-year project needs demonstrable routing, safe workflows, reproducible evaluation, and maintainable code. Distributed services would add deployment and consistency work before they provide a demonstrated benefit.

**Decision:** Use a React/TypeScript/Vite frontend, a FastAPI/Pydantic backend, and PostgreSQL. Keep identity, catalog/orders, conversation state, intent classification, knowledge retrieval, policies, workflows, routing, generation, tickets, and audit as separate Python modules within one backend. Use SQLAlchemy for persistence and Alembic for migrations.

**Consequences:** Local setup and database transactions remain straightforward. Module boundaries require disciplined interfaces and tests. Redis, task queues, and separate model/routing services are deferred until measured needs justify them; bounded local ingestion and request processing are sufficient for the initial demo scale.

**Alternatives considered:** Microservices add operational overhead; a monolithic chatbot prompt gives poor control over policy and permissions; n8n or another hosted workflow platform conflicts with the custom implementation requirement.

## ADR-002: Require a local deployment with no paid dependency

**Status:** Draft selected direction.

**Context:** The project must be reproducible without paid hosting, subscriptions, proprietary databases, or a proprietary desktop container runtime.

**Decision:** Treat native execution on an existing computer as the reference deployment. Permit an optional Podman-based setup after it is validated. Application libraries, database, and development tooling must meet the open-source requirement. OpenRouter is the only permitted external hosted model API and is an explicit external-service exception, not an open-source application component.

**Consequences:** No Docker Desktop dependency or cloud deployment is required. Hardware, local storage, installation access, and optional internet connectivity are still practical requirements. No paid provider route, automatic credit purchase, hosted embedding service, or paid add-on may be enabled as a fallback.

**Alternatives considered:** Managed databases and paid hosting simplify some operations but conflict with the project constraint. Containers are optional packaging, not a condition for using the system.

## ADR-003: Keep operational data and knowledge vectors in PostgreSQL

**Status:** Draft selected direction.

**Context:** Orders, conversations, requests, assignment, and audit need transactional consistency. The initial approved knowledge collection is small enough to avoid a separate search service.

**Decision:** Use PostgreSQL for structured data and pgvector for local knowledge-vector search. Store approved knowledge versions, chunk metadata, visibility, and embedding provenance alongside vector records. Filter active, approved, authorized content during retrieval. Use local sentence-transformer embeddings, initially the `sentence-transformers/all-MiniLM-L6-v2` candidate whose license evidence appears in the technology stack; pin its revision and evaluate retrieval before adoption.

**Consequences:** One database supports both business transactions and retrieval. Installing pgvector must be validated for the reference environment. Embedding dimension or model changes require a versioned re-index. Structured facts such as prices, inventory, and order state remain database reads, not vector-search answers.

**Alternatives considered:** A separate vector database increases setup and backup complexity. Hosted embeddings add an unauthorized provider/cost boundary. Pure keyword retrieval can remain a comparison or limited fallback, but is not equivalent to the selected semantic retrieval design.

## ADR-004: Separate trained intent routing from pretrained answer generation

**Status:** Draft selected direction.

**Context:** The FYP needs an assessable contribution beyond connecting a chat UI to a model API. Intent recognition, policy eligibility, staff assignment, and fluent wording have different correctness requirements.

**Decision:** Train a local TF-IDF/scikit-learn intent classifier using labeled synthetic conversations. Compare keyword routing, classifier-only routing, and classifier-plus-rule routing. Application-owned rules combine predictions with conversation state, verified order facts, permissions, and staff availability. Use pretrained local embeddings for retrieval and a pretrained hosted model only for grounded answer generation.

**Consequences:** Intent training and routing can be reproduced without the hosted generator. Classifier uncertainty requires validation, clarification, and fallback behavior. Do not describe inference through OpenRouter or local embedding inference as training a language model. Fine-tuning a language model is outside the initial scope.

**Alternatives considered:** An LLM-only router is easy to prototype but mixes language behavior with consequential decisions. A keyword-only router is useful as a baseline but likely limited on paraphrases; that limitation must be measured rather than assumed as a result.

## ADR-005: Restrict OpenRouter to an explicitly reviewed free route

**Status:** Draft selected direction; a candidate is recorded, but live integration and task evaluation remain pending.

**Context:** Free route availability, pricing, and model licenses can change. A route advertised as free does not establish the underlying model's license, and a general free router may choose unreviewed models.

**Decision:** Use a narrow backend HTTPX adapter with an explicitly configured allowlisted model identifier. The example configuration names candidate `google/gemma-4-31b-it:free`; the technology stack records the catalog and license review. Evaluate the candidate for the task and check current route pricing before activation. Validate zero-cost route metadata, revalidate after configuration changes and on a bounded schedule, and fail closed when eligibility is unknown. Use provider price caps where supported. Disable paid fallback, paid tools, and general automatic model routing outside the reviewed allowlist.

**Consequences:** Live generation may be unavailable when a model disappears or its eligibility cannot be established. Bound request size, token output, timeouts, concurrency, and retries. Store the API key only in ignored backend configuration, keep secrets blank in tracked examples, and default to offline mode. Log model ID, prompt/knowledge versions, latency, and outcome without secrets. Naming a candidate is not evidence of an already-working integration or a guarantee of future price, availability, or quality.

**Alternatives considered:** Automatically choosing any available free model avoids configuration effort but defeats license review. Paid fallback contradicts the requirement. Running a larger local answer model may be reconsidered if available hardware and evaluated quality justify it, but is not required now.

## ADR-006: Use server-side sessions and resource-scoped authorization

**Status:** Draft selected direction.

**Context:** Customer orders and support conversations require identity and ownership checks independent of generated content. Browser access also requires protection against cross-site state-changing requests.

**Decision:** Use seeded synthetic accounts, reviewed password hashing, and revocable server-side sessions with opaque cookie tokens. Store token hashes server-side. Apply customer/support/admin roles and resource ownership/team scope in backend services. Use HttpOnly cookies, an appropriate SameSite policy, Secure cookies on HTTPS, explicit origin checks, and session-bound CSRF protection for unsafe authenticated requests. Restrict any HTTP development exception to documented loopback use.

**Consequences:** Sessions need storage, expiry, rotation, and revocation. The backend never accepts a model-supplied customer identity as authority. Staff access is scoped to authorized support work. Password recovery and self-service registration are deferred; local seeded accounts are enough for the first demonstrable workflow.

**Alternatives considered:** Client-stored bearer tokens add exposure to browser script and refresh/revocation complexity for this scope. A customer ID in a chat message is not authentication.

## ADR-007: Make confirmed synthetic actions transactional and idempotent

**Status:** Draft selected direction.

**Context:** A repeated click, network retry, concurrent request, or changed order state must not cancel an order twice, create duplicate return requests, or bypass current policy.

**Decision:** Present a structured proposal before material writes. On confirmation, recheck identity, ownership, proposal expiry, current facts, policy, and overlap constraints inside a transaction. Bind an idempotency key to actor, operation, and validated payload. Use database constraints, row locks, and allowed-transition checks to prevent duplicates even across different keys. Atomically commit either an eligible synthetic order's transition to `cancelled` or creation/update of a return request, together with its audit event, consumed proposal, and stored retry result.

**Consequences:** Stale proposals can require new confirmation. A reused key with different input is a conflict. Generation happens outside the write transaction. Failed wording generation falls back to a cancellation receipt reporting the committed synthetic order state, or a return-request receipt reporting the created request and its status. The first MVP can cancel eligible local demo orders exactly once; returns remain request intake. It does not execute real payments, refunds, carrier actions, or live-store writes.

**Alternatives considered:** Trusting the preview or model decision at execution creates a time-of-check gap. In-memory duplicate checks fail across concurrent workers and restarts.

## ADR-008: Make handoff and staff assignment explicit and explainable

**Status:** Draft selected direction.

**Context:** Some requests are ambiguous, unsupported, or require human review. Users should not repeat all known information, and staff should understand why a ticket was assigned.

**Decision:** Route through versioned intent-to-team and priority rules, then continuity, availability, language, and simple workload checks. Recheck assignments transactionally. Record reasons and factual inputs. Queue tickets unassigned when no eligible staff member is available. Include verified facts, unresolved intents, attempted actions, evidence references, and the handoff reason in the staff summary. After the one-time handoff receipt, suppress automated assistant replies in both `handoff_pending` and `human_owned`. Recheck state before sending any in-flight generated response and suppress it if either state has been entered.

**Consequences:** Routing is auditable and can be evaluated independently of answer fluency. Staff availability is explicit synthetic application data, not an inferred real-world schedule. A primary ticket retains multiple unresolved intents; linked subtickets are deferred. Manual assignment changes remain permission-checked and audited.

**Alternatives considered:** Sentiment-only priority can misclassify urgency. Round-robin assignment alone ignores eligibility and continuity. Letting both the assistant and staff reply without ownership state creates conflicting guidance.

## ADR-009: Keep useful, labeled behavior when generation is unavailable

**Status:** Draft selected direction.

**Context:** A free external route can fail, exhaust quota, or become ineligible. The demo and most tests still need to demonstrate actual workflows.

**Decision:** Provide deterministic local responses for verified facts, policy decisions, synthetic cancellation receipts, return-request receipts, and handoffs. Clearly mark offline/fallback mode and record that no successful live inference occurred. Missing knowledge triggers clarification or a ticket. Database failure must never produce a fabricated successful cancellation, return request, or handoff.

**Consequences:** Core order/request/routing behavior remains testable without network access. Offline wording is less flexible and is not evidence of hosted model answer quality. Failed classifier loading uses a conservative, recorded keyword/clarification path rather than an invented prediction.

**Alternatives considered:** Blocking all workflows on model availability makes the demo fragile. Presenting canned replies as live model output misrepresents implementation and evaluation.

## ADR-010: Version artifacts and evaluate components separately

**Status:** Draft selected direction.

**Context:** Academic results must be reproducible where possible, and grounded answers need provenance. Hosted generation is less reproducible than deterministic local decisions.

**Decision:** Version datasets, label schemas, splits/seeds, classifier artifacts, policies, routing rules, knowledge/chunks, embedding configuration, prompts, and model selections. Split by complete conversation and group near-duplicate paraphrases. Use pytest, Vitest/React Testing Library, and Playwright for relevant behavior. Default tests use a stubbed model adapter; live API checks are separately enabled after eligibility review.

**Consequences:** Evaluation compares measured macro-F1, per-class errors, routing correctness, grounded-answer quality, workflow success, handoff quality, and latency. Store actual commands and outcomes in the appropriate versioned evidence. No performance figures or passing test results are claimed here. Record hosted settings and outcomes without promising exact replay of remote model output.

**Alternatives considered:** Random utterance-level splitting can leak conversation context and paraphrases. A single chatbot satisfaction score obscures authorization, routing, and action failures.
