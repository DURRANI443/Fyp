# Changes from v0.1.0

Date: 2026-10-24 (Asia/Karachi).

- Implemented React/TypeScript customer, support and admin screens with ordinary CSS and locally authored illustrations.
- Implemented FastAPI authentication, database sessions, role/ownership checks, CSRF checks, migrations and synthetic seed data.
- Implemented approved policy retrieval, intent classification, order tracking, confirmation-based cancellations and return requests, routing, summaries, staff ownership and replies.
- Implemented knowledge versions, approval controls, team availability, audit history and basic metrics.
- Added a fail-closed free-route OpenRouter adapter. Live testing is pending the user's key; no successful live generation is claimed.
- Added isolated backend, frontend and browser tests plus a versioned synthetic intent/retrieval dataset and measured evaluation.
- Changed the immediate demo default from PostgreSQL/pgvector to embedded SQLite. PostgreSQL remains an optional relational deployment; local embedding vectors are cached in process, not stored in pgvector.
- Added a reproducible local setup/start workflow and actual implementation diagrams. The v0.1.0 requirements remain the reference; partially completed criteria are identified in traceability.
