# v0.2.0 verification record

Date: 2026-10-24 (Asia/Karachi). Executed checks for the captured local MVP milestone.

## Environment

Windows; Python 3.13.14; Node 24.14.1; npm 11.11.0. Backend packages are pinned in `backend/requirements.txt`; optional CPU embedding packages in `backend/requirements-ai.txt`; frontend and diagram packages in their npm lockfiles. `pip check` reports no broken requirements. Root and frontend npm audits reported zero known vulnerabilities at installation; this is a point-in-time package audit, not a security certification.

## Observed checks

| Check | Observed result | Scope |
| --- | --- | --- |
| Final SQLite API/AI suite | **64 passed in 18.43 seconds** | 9 core, 25 support, 30 AI cases; [captured output](evidence/backend-sqlite.txt) |
| PostgreSQL migration/seed | Passed | PostgreSQL 17.11 native binaries; Alembic upgrade from empty database, synthetic seed |
| PostgreSQL backend suite | **64 passed in 145.68 seconds** | 9 core, 25 support, 30 AI cases; each database-dependent test used a new isolated schema |
| API and application response | Passed | `/api/health` returned HTTP 200/version 0.2.0/database sqlite; `/` returned 200 with built frontend |
| Frontend typecheck/production build | Passed | TypeScript project build and Vite assets |
| Frontend unit/component suite | **11 passed in 8.33 seconds** | CSRF/session expiry, demo login, confirmation, retry IDs, closed/human-owned states |
| Browser workflows | **4 passed in 53.2 seconds** | Actual built frontend and API, isolated SQLite, offline mode and deterministic TF-IDF retrieval; no mocked endpoints |
| Local neural retrieval | **13/13 smoke cases passed** | Actual `local_sentence_transformer` mode; [measured report](evidence/retrieval-local-transformer.json); approximately 60.5s cold initialization and 16–44ms warm fixture queries |
| TF-IDF retrieval fallback | **13/13 smoke cases passed** | [Measured report](evidence/retrieval-tfidf.json); small synthetic corpus, not an independent benchmark |
| Setup script | Passed | `scripts/setup.ps1`: dependency installation, npm clean install, production build, migration and preserved existing data |
| Startup with cached neural model | Passed | `scripts/start.ps1`: local model warms before application readiness; reports `local_sentence_transformer` |
| Connected neural policy response | Passed | Customer sign-in, new chat and cited local answer; 346ms after warmup in the [running-app smoke](evidence/running-app-smoke.json) |
| Mermaid exports | 3 passed | Architecture, support flow and actual schema; [render record](evidence/diagram-render.json) |
| Live OpenRouter inference | **NOT RUN** | User key not yet configured; no successful live answer or live quality result claimed |

The PostgreSQL server was an isolated loopback-only validation cluster using downloaded official PostgreSQL binaries, not a system service or public database. It has no pgvector extension. The regular application remains configured for SQLite. `TEST_POSTGRES_URL` enables optional relational testing against a dedicated test database; the fixture creates randomly named `northstar_test_*` schemas and removes only those schemas after each test. Do not point test configuration at a production database.

## Browser evidence

The four Playwright workflows cover policy citations and human queue/claim/reply/resolution; cancellation confirmation/back-out plus return submission and staff approval; admin knowledge approval/team persistence/audit history; and mobile navigation, eligibility, chat and horizontal-overflow checks. Browser fixtures deliberately use TF-IDF for deterministic startup. Real local neural retrieval and startup are independently exercised above; browser results do not establish live OpenRouter operation.

Reviewed screenshots: [login](evidence/login-desktop.png), [customer catalog](evidence/customer-desktop.png), [cited chat](evidence/grounded-chat-desktop.png), [staff inbox](evidence/staff-inbox-desktop.png), [admin knowledge](evidence/admin-knowledge-desktop.png), [mobile catalog](evidence/customer-mobile.png), and [mobile support](evidence/support-mobile.png). The sampled desktop and mobile layouts render without horizontal page overflow; this is not a complete accessibility audit.

The setup script was rerun successfully after stopping Vite: Windows had initially refused to replace a native dependency held open by the running development server. The runbook now explicitly instructs stopping Vite/tests before reinstalling dependencies.

## Important behavior covered

- Session-cookie properties, hashed server-side sessions, login failure, CSRF and origin checks, customer ownership and staff/admin role boundaries.
- Cancellation and return eligibility, quantity limits, proposal expiry and changed order/policy detection, idempotency conflicts, concurrent action confirmation and competing staff claims.
- Explicit handoff, immediate assistant pause, generation outside a database transaction, suppression of an in-flight answer after handoff, ticket ownership, return review and resolution.
- Negated changes, mixed late/cancel requests, unknown order references, return clarification and human/billing interruption of a pending clarification.
- Approved knowledge selection including draft behavior; local retrieval failure fallback; provider metadata, timeout/rate/error paths, paid-route rejection, endpoint restrictions, redaction, citation/number validation and rejected action claims.

Individual tests and requirement mappings are linked in [traceability](requirements-traceability.md). Evaluation figures and per-class failures belong in [AI evaluation](ai-evaluation.md), not in a claim that every natural-language request works correctly.

## Remaining verification limits

No real OpenRouter key has been used. Independent customer data, human-rated grounded-answer quality, statistically useful load/performance testing, complete accessibility auditing, external penetration testing, real shop/carrier/payment integrations and production deployment are not verified. The UI/browser smoke checks and local synthetic tests do not establish production readiness. The classifier has poor unknown-class recall on its small synthetic test set; application safety also relies on server-side ownership, workflow checks, confirmations and human fallback.

The in-app browser integration was unavailable in this environment (no connected browser surfaces). Automated Playwright checks and locally captured screenshots provide browser verification; no visible in-app preview handoff is claimed.
