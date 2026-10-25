# Increment process and deployment handoff

The v0.3.0 increment began on 2026-10-24 and was saved as checkpoint commit `7f779ef` when the user requested pausing work. It resumed on 2026-10-25. The original three documentation baselines remain unchanged.

1. Translate the requested catalog, fake payment and selected hosting stack into [requirements](requirements.md).
2. Extend the schema additively, keep original order snapshots, implement authoritative checkout and preserve authentication/ownership boundaries.
3. Implement the cart, reviewed totals, payment outcomes and retry recovery. Fix the discovered background-completion race with a regression test.
4. Validate SQLite and PostgreSQL migrations/workflows, frontend behavior, production build, all eight browser workflows, and ARM dependency availability. Correct browser test selectors/question submission during integration.
5. Update the [API contract](api-contract.md), diagrams, [traceability](traceability.md), deployment instructions and actual verification evidence. Render and inspect diagrams before capture.
6. Capture the documentation manifest, check exact Git blob hashes for prior baselines, and publish the implementation to the selected GitHub repository.
7. The owner creates the provider resources and chooses account passwords, database credentials and hostnames. Follow [deployment](deployment.md), run its deployed smoke checks and record the real hosting evidence in the next documentation version.

GitHub Actions checks the application/browser workflows and a separate PostgreSQL service. Its hosted runner results are independent of local test results. No desktop-control/manual audit, cloud provisioning, or successful live model inference is inferred from passing local tests.
