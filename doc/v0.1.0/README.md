# v0.1.0 - SDLC foundation

Date: 2026-10-24 (Asia/Karachi)

Status: **Captured documentation baseline.** This is the initial planning/design baseline, not a working application release or supervisor approval. [The manifest](manifest.json) records the captured file inventory and SHA-256 hashes.

## What this baseline contains

- Canonical project instructions and an open-source/free-service boundary.
- A project charter, incremental SDLC, and implementation milestones.
- 17 functional requirements, 10 nonfunctional requirements, eight use cases, and requirement-to-test traceability.
- Technology/license decisions, a modular system design, and architecture decision records.
- Seven planned system/process diagrams: context, components, use cases, data model, support sequence, ticket lifecycle, and SDLC process.
- An evaluation plan that compares keyword, classifier, and hybrid routing while testing workflow correctness separately.

## Reading order

1. [Project charter and scope](planning/project-charter.md)
2. [Software requirements](requirements/software-requirements.md)
3. [Use cases and acceptance scenarios](requirements/use-cases.md)
4. [Technology stack, license sources, and cost boundaries](architecture/technology-stack.md)
5. [System design and proposed API contracts](architecture/system-design.md)
6. [Architecture decisions](architecture/decisions.md)
7. [Diagram index](diagrams/README.md)
8. [SDLC process and milestones](planning/sdlc-plan.md)
9. [Testing and evaluation strategy](planning/testing-evaluation-strategy.md)
10. [Requirement traceability](requirements/traceability-matrix.md)
11. [Change log](CHANGELOG.md) and [verification record](verification.md)

The [project instruction snapshot](project-instructions.md) preserves the rules used for this baseline. The root [agent.md](../../agent.md) remains the live instruction file for future work.

## Scope and next increment

All product requirements are planned. No frontend/API/database, trained classifier, or live OpenRouter inference is delivered by this documentation version. The only executable project tooling in this increment concerns documentation checking and rendering.

v0.2.0 is the planned application foundation: frontend/backend structure, locked dependencies, PostgreSQL migration setup, synthetic seed framework, local health checks, and validated run instructions. Subsequent versions deliver the product slices described in the SDLC plan.

Captured baseline changes must go in the next version; see [documentation conventions](../README.md).
