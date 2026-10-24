# Use cases and acceptance scenarios

Version: v0.1.0  
Baseline date: 2026-10-24 (Asia/Karachi)  
Status: Planned scenarios; all execution outcomes are **NOT RUN**.

## UC-01: Ask a policy or product question

Actor: Customer. Preconditions: An authenticated conversation and approved knowledge exist.

1. The customer asks a question.
2. The system identifies the intent and retrieves relevant approved knowledge.
3. For changing product facts such as stock or price, the system reads the database.
4. The system answers with document/version references where policy evidence is used.
5. If evidence is absent, conflicting, or insufficient, it asks a useful clarification or offers handoff.

Acceptance: A supported return-policy answer cites the active policy version. An unsupported warranty claim is not invented. Withdrawn documents cannot ground an answer. Instructions embedded in a document do not alter permissions.

Requirements: FR-003–FR-006, FR-014–FR-016, NFR-004, NFR-008.

## UC-02: Track an owned order

Actor: Customer. Preconditions: The customer is authenticated and synthetic order data is seeded.

1. The customer requests order status and selects an order if needed.
2. The backend verifies ownership using authenticated identity.
3. The system reads current order and simulated shipment facts.
4. It explains the current state; a configured delivery exception can create a logistics ticket.

Acceptance: The owner receives current stored status. Supplying another customer's order reference reveals no order content. Missing tracking information is described as unavailable rather than fabricated.

Requirements: FR-001–FR-004, FR-007, FR-010, FR-016, NFR-002.

## UC-03: Cancel an eligible demo order

Actor: Customer. Preconditions: An owned order exists; cancellation rules are configured.

1. The system checks ownership and cancellation eligibility.
2. It shows the affected order and the proposed change.
3. The customer confirms the specific action before expiry.
4. The backend rechecks eligibility and performs the transaction using a scoped idempotency key.
5. The system returns the stored outcome and records an audit event.

Acceptance: Without confirmation, no state changes. If fulfillment changes before execution, cancellation is rejected with a useful explanation. A network retry produces one cancellation and the same result. A reused key with a different payload is rejected.

Requirements: FR-008, FR-016, NFR-002, NFR-003, NFR-008.

## UC-04: Request a return

Actor: Customer. Preconditions: An owned order item and configured return policy exist.

1. The customer selects the item and supplies a reason.
2. The system checks delivery date, configured eligibility, and existing requests.
3. It explains the decision and previews the return request.
4. On confirmation, it creates one request and assigns the returns queue as required.
5. Staff can review exceptions. No actual refund or label purchase occurs.

Acceptance: Eligible requests persist once with policy version and reason. Boundary-date and excluded-item decisions match configuration. An ineligible request is explained and can be escalated without bypassing policy.

Requirements: FR-009–FR-011, FR-016, NFR-003, NFR-008.

## UC-05: Resolve a mixed request

Actor: Customer. Example: “My order is late; cancel it.”

1. The system retains both the delivery concern and cancellation request.
2. It verifies the order and checks present fulfillment state.
3. It offers a confirmed cancellation only when eligible.
4. It routes the unresolved delivery issue or cancellation exception with relevant context.

Acceptance: A shipped order cannot be canceled through generated instructions. Completing one part does not silently discard the other. The routing reason identifies the relevant fact/rule and outstanding need.

Requirements: FR-004, FR-007, FR-008, FR-010, FR-011, NFR-008.

## UC-06: Transfer to a person

Actors: Customer and support staff. Trigger: Customer request, repeated unresolved issue, unsupported intent, or failed workflow requiring review.

1. The system creates or updates a ticket with a summary and routing reason.
2. It enters pending-human state and pauses automated replies.
3. An authorized staff member claims the ticket; the system enters human-owned state.
4. Staff sees verified facts, attempted actions, and unresolved needs and replies to the customer.
5. Staff resolves the ticket or explicitly returns the conversation to the assistant.

Acceptance: No available staff leaves the ticket visibly queued. Two simultaneous claims produce one owner. Further customer messages reach the human queue without assistant replies. Resolution alone does not silently resume the assistant.

Requirements: FR-010–FR-012, FR-016, NFR-002, NFR-006.

## UC-07: Update approved knowledge or rules

Actor: Administrator. Preconditions: Admin authentication and a valid change exist.

1. The administrator adds or updates knowledge or configuration.
2. Validation checks required fields and allowed settings.
3. The system records a version, actor, and timestamp.
4. Approved knowledge becomes retrievable; withdrawn versions are excluded from new answers.
5. Subsequent actions evaluate the applicable current policy.

Acceptance: Support/customer roles cannot activate a policy. A generated answer retains the version it used. A pending action is rechecked against current eligibility before execution.

Requirements: FR-005, FR-013, FR-016, NFR-008, NFR-010.

## UC-08: Continue when live generation is unavailable

Actor: Customer. Trigger: Missing key, disabled live mode, model/license/price validation failure, timeout, or exhausted quota.

1. The adapter refuses or ends the bounded live request.
2. The system gives a labeled deterministic fallback and preserves conversation state.
3. Local order workflows remain available; unresolved questions can become tickets.
4. An outcome record distinguishes fallback from successful live generation.

Acceptance: No alternative paid route or external model provider is called. No secret appears in the response. Retries remain bounded and a failed call does not produce a fabricated answer.

Requirements: FR-014–FR-016, NFR-001, NFR-002, NFR-004.

