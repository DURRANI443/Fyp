# SDLC process for this increment

Date: 2026-10-24 (Asia/Karachi). Method: iterative implementation with retained milestone baselines.

| Stage | Work performed | Retained artifact |
| --- | --- | --- |
| Planning | Re-scoped the original phased plan for a solo, same-day English MVP using default styling and synthetic store data | [Change log](CHANGELOG.md), [implementation scope](implementation.md) |
| Requirements | Preserved original FR/NFR identifiers; identified implemented, partial and deferred criteria | [Traceability](requirements-traceability.md) |
| Design | Defined frontend/backend DTOs, relational entities, confirmation rules and human ownership before parallel implementation | [API contract](api-contract.md), [diagrams](diagrams/README.md), [AI design](ai-design.md) |
| Implementation | Built customer, staff and admin UI, API, migrations, local classification/retrieval and optional generation adapter | Versioned source tree and dependency locks |
| Verification | Exercised policy boundaries, ownership, races, retries, role access, provider failure handling and connected browser workflows | [Verification record](verification.md), [AI evaluation](ai-evaluation.md) |
| Release preparation | Added repeatable startup, explicit key setup, demo walkthrough and limitations; captured document file hashes | [Runbook](runbook.md), milestone manifest |
| Maintenance | Further edits use the next documentation version after capture; preserve old versions and record changed behavior/tests | [Version conventions](../README.md) |

The user is the sole student owner. Implementation assistance does not establish supervisor approval, independent annotation or an externally reviewed research result. The records separate intended requirements, executed tests, synthetic measurements and deferred work.

## Change control

Keep the canonical [project instructions](../../agent.md) current and retain the [instruction snapshot](agent-instructions.md) for this milestone. Changes to policies, routing, model/license choices, schema or action semantics require the corresponding implementation, test and documentation updates. A new model must be reviewed and explicitly allowlisted before use. A captured manifest is never silently regenerated to hide an edit.

Local Git tracks source history when commits are made; the manifest provides document integrity independently. No Git remote, public deployment, paid service registration or external customer communication is part of this milestone.
