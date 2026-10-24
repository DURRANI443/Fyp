# Requirements traceability matrix

Version: v0.1.0  
Baseline date: 2026-10-24 (Asia/Karachi)  
Status: Test IDs are planned specifications, not existing test files. Every outcome is **NOT RUN**.

Backlog increments are defined in [the SDLC plan](../planning/sdlc-plan.md). Test methods and evidence requirements are defined in [the evaluation strategy](../planning/testing-evaluation-strategy.md).

| Requirement | Use case | Backlog increment | Planned verification ID and scope | Outcome |
| --- | --- | --- | --- | --- |
| FR-001 | UC-02, UC-06, UC-07 | INC-03 | T-AUTH: login, role matrix, invalid/expired sessions | NOT RUN |
| FR-002 | UC-02 | INC-03 | T-ORDERS: seeded catalog, owned history, cross-customer denial | NOT RUN |
| FR-003 | UC-01, UC-02 | INC-03 | T-CHAT: persistence, ordering, unauthorized reads/writes | NOT RUN |
| FR-004 | UC-01, UC-02, UC-05 | INC-04 | T-INTENT: supported intents, ambiguity, follow-up context, mixed requests | NOT RUN |
| FR-005 | UC-01, UC-07 | INC-04 | T-RETRIEVAL: local indexing, source versions, approval/withdrawal | NOT RUN |
| FR-006 | UC-01 | INC-04 | T-GROUNDING: supported/unsupported answers, citations, fact provenance | NOT RUN |
| FR-007 | UC-02, UC-05 | INC-03 | T-ORDER-STATUS: current facts, missing tracking, simulated exception | NOT RUN |
| FR-008 | UC-03, UC-05 | INC-05 | T-CANCEL: preview, confirmation, expiry, stale state, transaction | NOT RUN |
| FR-009 | UC-04 | INC-05 | T-RETURN: date boundaries, exclusions, confirmation, duplicate request | NOT RUN |
| FR-010 | UC-02, UC-04–UC-06 | INC-04, INC-05 | T-ROUTING: rule precedence, queue/priority/reason, unavailable staff | NOT RUN |
| FR-011 | UC-04–UC-06 | INC-05 | T-HANDOFF: summary, pending-human pause, no lost context | NOT RUN |
| FR-012 | UC-06 | INC-05 | T-STAFF: queue access, claim race, replies, resolve, explicit resumption | NOT RUN |
| FR-013 | UC-07 | INC-05 | T-ADMIN: role denial, configuration validation, versioned changes | NOT RUN |
| FR-014 | UC-01, UC-08 | INC-04 | T-MODEL-GATE: allowlist, license/price eligibility, failure handling | NOT RUN |
| FR-015 | UC-08 | INC-04 | T-OFFLINE: disabled generation, honest labels, local workflow continuity | NOT RUN |
| FR-016 | UC-01–UC-08 | INC-04, INC-05 | T-AUDIT: provenance, action outcome, credential/PII redaction | NOT RUN |
| FR-017 | Evaluation experiment | INC-06 | T-EVALUATION: frozen split, three baselines, reproducible reports | NOT RUN |
| NFR-001 | UC-08 | INC-02, INC-04 | T-LICENSE: dependency/model inventory, pins, free-route configuration | NOT RUN |
| NFR-002 | UC-02, UC-03, UC-06–UC-08 | INC-03–INC-05 | T-SECURITY: secrets, hashing, role/ownership bypass, model-payload minimization | NOT RUN |
| NFR-003 | UC-03, UC-04 | INC-05 | T-IDEMPOTENCY: retries, mismatched payloads, concurrent execution, rollback | NOT RUN |
| NFR-004 | UC-01, UC-08 | INC-04 | T-RESILIENCE: size/token/time/retry/concurrency limits and failing metadata | NOT RUN |
| NFR-005 | Setup and experiment | INC-02, INC-06 | T-REPRODUCE: clean setup, seeds/migrations, keyless tests, experiment rerun | NOT RUN |
| NFR-006 | UC-01–UC-08 | INC-03, INC-05 | T-ACCESSIBILITY: keyboard flow, labels, text feedback, ownership/mode visibility | NOT RUN |
| NFR-007 | UC-02, UC-06 | INC-06 | T-PERFORMANCE: specified local load, p50/p95 and separate model timings | NOT RUN |
| NFR-008 | UC-01, UC-03–UC-05, UC-07 | INC-04, INC-05 | T-POLICY-BOUNDARY: injection, forged identity/actions, deterministic policy checks | NOT RUN |
| NFR-009 | All implementation | INC-02–INC-05 | T-MAINTAINABILITY: module review plus meaningful backend/UI checks | NOT RUN |
| NFR-010 | Baseline capture | INC-01–INC-07 | T-DOCS: links, stable IDs, change log, status, manifest integrity | NOT RUN |

When implementation begins, add actual test file/function links and evidence links in the next baseline. Preserve this table as the original plan rather than backfilling it with later outcomes. A single test may verify multiple requirements, but each requirement needs identifiable evidence.

