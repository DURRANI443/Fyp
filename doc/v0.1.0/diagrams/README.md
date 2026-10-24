# Planned system diagrams

Baseline: `v0.1.0`  
Date: 2026-10-24 (Asia/Karachi)  
Status: **PLANNED architecture and workflows; application features are not implemented.**

These Mermaid sources describe the proposed final-year project. They are design evidence, not proof of a running application, database migration, model integration, or tested workflow.

## Diagram inventory

| Source | SVG export | Purpose |
| --- | --- | --- |
| [system-context.mmd](system-context.mmd) | [View](system-context.svg) | Actors, the local application boundary, and the only permitted hosted runtime service: OpenRouter. |
| [component-architecture.mmd](component-architecture.mmd) | [View](component-architecture.svg) | React interface, modular FastAPI backend, application-owned routing, local retrieval, database, and guarded model adapter. |
| [use-cases.mmd](use-cases.mmd) | [View](use-cases.svg) | Customer, support, and administrator use cases, represented explicitly as a flowchart rather than UML use-case notation. |
| [data-model.mmd](data-model.mmd) | [View](data-model.svg) | Conceptual relational schema, including access control, commerce, support, knowledge versions, actions, and audit records. |
| [support-sequence.mmd](support-sequence.mmd) | [View](support-sequence.svg) | Request processing, authorization, evidence retrieval, free-route checks, model failure, and human handoff. |
| [ticket-lifecycle.mmd](ticket-lifecycle.mmd) | [View](ticket-lifecycle.svg) | Proposed ticket transitions and their relationship to conversation ownership. |
| [sdlc-process.mmd](sdlc-process.mmd) | [View](sdlc-process.svg) | Increment planning, design, implementation, verification, release evidence, and immutable baseline capture. |

## Scope and assumptions

- Reference deployment is local on an existing computer. Application libraries and development tools are open source. OpenRouter is a permitted external service exception; it is not described as open source.
- Live generation may use only an explicitly allowlisted free model route with reviewed model licensing and verified zero-cost metadata. An unavailable or ineligible route produces a useful fallback or handoff. No paid fallback is permitted.
- The first deliverable is documentation. Later increments are intended to implement real local PostgreSQL persistence, authorization, routing, and order workflows. This baseline contains no application implementation.
- Catalog, customers, orders, shipping updates, and displayed payment statuses use seeded synthetic data. Checkout/order creation, exchanges, payment processing, payment-card storage, carrier integration, and live merchant writes are outside this baseline's application scope.
- One customer-facing assistant orchestrates bounded workflows. The classifier proposes intent; backend rules decide eligibility, access, routing, and actions. Generated text does not authorize an operation.
- Approved policy documents supply policy evidence. The database supplies current product, inventory, order, and return-action facts. Retrieved text and customer messages remain untrusted input.
- Customers authenticate before private order access. Backend code verifies customer ownership for each lookup and action. Support and administrator permissions are checked server-side.
- Material order changes require explicit confirmation, current eligibility checks, transactions, and duplicate prevention. An action request records the intended operation; its presence does not mean execution succeeded.
- Both `handoff_pending` and `human_owned` pause assistant generation and bot replies. The interface may show transport acknowledgment and actual queue status. Staff acceptance changes ownership to `human_owned`; staff explicitly returns assistant ownership or closes the conversation.
- A conversation can have multiple historical tickets, with at most one active ticket enforced by application/database rules in implementation. Assignment records retain transfers and identify the assigned team and staff member.
- Knowledge document rows represent immutable versions under a shared `document_key`. Chunks store their document version, embedding model, embedding version, and vector; the eventual migration must fix the embedding dimension and compatible index. Answer citations reference specific chunks.
- Entity types, indexes, constraints, retention, and enum values are provisional. The ERD is a conceptual model, not executable SQL. Implementation must add foreign-key indexes, uniqueness constraints, and transaction rules.

## SRS entity mapping and omissions

The ERD condenses some concepts listed in the SRS and deliberately omits details needed by the eventual physical schema. The following mappings describe design intent, not completed persistence behavior.

| SRS concept | Representation and remaining design work |
| --- | --- |
| `ShipmentEvent` | Omitted as a separate entity. `ORDERS.demo_shipping_status` holds only the latest synthetic status; timestamped shipping-event history still needs a separate table or explicitly specified event representation. |
| `ReturnRequest` | Consolidated into `ACTION_REQUESTS` with a return action type, requested item parameters, and status. Detailed return receipt, inspection, and outcome history is not modeled; a later design must add it if included in the implemented return workflow. |
| `ActionConfirmation` | Summarized by `ACTION_REQUESTS.confirmed_at`, requester identity, and requested parameters. Confirmation expiry and an immutable binding to the exact confirmed operation are not yet represented; these must be designed before material actions execute. |
| `IdempotencyRecord` | Summarized by the unique `ACTION_REQUESTS.idempotency_key`, status, and result summary. Request fingerprints, concurrent execution control, and durable replay results still require explicit physical design. A unique key alone is insufficient. |
| `ConfigurationVersion` | Referenced through ticket routing-rule, action policy, message prompt, and chunk embedding version columns. Immutable configuration contents and their version registry are omitted; implementation must retain the exact configuration needed to reproduce each decision. |

These omissions do not remove the corresponding requirements. Resolve the physical schema and update the ERD, migrations, and traceability records in the implementation baseline.

## Source and export convention

Editable `.mmd` files are authoritative. Any generated diagram export must use the same basename in this directory, for example `support-sequence.mmd` and `support-sequence.svg`. Regenerate the export whenever its source changes within a draft baseline; never hand-edit an export independently.

All seven sources have matching rendered SVG exports in this baseline. An overview visual check and label-boundary inspection were performed; details and limitations are in the [verification record](../verification.md). The dense ERD and sequence diagram are scalable exports intended to be opened and zoomed, not squeezed into an unreadable report thumbnail.

Once a baseline is captured, preserve both source and export files and their manifest hashes. Later revisions belong in the next version directory. Git records edits; version directories preserve milestone snapshots.
