# Checkpoint verification

Date: 2026-10-24. Status: **unfinished checkpoint**, saved because the user requested pushing the current code and continuing later. Do not treat this draft as a fully tested release or a completed cloud deployment.

| Check | Observed result |
| --- | --- |
| SQLite backend `pytest tests -q` | 95 passed in 13.70 s, including checkout and deployment/account tests. Local console record: `.local/backend-v030-sqlite.txt` (ignored). |
| Checkout behavior | Approved/declined scenarios, authorization, CSRF, ownership, authoritative prices, duplicate retries, last-item concurrency, cancellation restock/refund, and new order references covered. |
| Existing SQLite upgrade | Read-only backup of existing database upgraded to `91bb428af032`; existing 4 users, 5 orders, 7 items, 5 conversations and 4 tickets preserved. Catalog became 10 products; foreign-key and Alembic drift checks passed. Original user database untouched. |
| Frontend typecheck | Passed for current source. |
| Frontend Vitest | 39 passed in 13.58 s before the final static image-credit file was added. |
| Production configuration/account tests | 14 passed; covered configuration rejection, account provisioning and session invalidation after password reset. Included in the backend suite above. |
| Vercel preflight | Placeholder refused; configured HTTPS endpoint accepted; invalid destinations rejected using temporary configuration. No real endpoint configured. |
| Production frontend build | NOT RUN for current checkpoint; local `dist` is stale and ignored. |
| Checkout browser tests | NOT RUN. Existing catalog browser assertion still expects 6 products instead of 10. |
| PostgreSQL v0.3.0 migration/tests | NOT COMPLETED. A fresh isolated PostgreSQL bootstrap attempted before server readiness failed; temporary servers stopped. Earlier v0.2.0 PostgreSQL evidence does not verify this increment. |
| Oracle ARM dependency dry-run | Completion not confirmed at checkpoint. |
| Mermaid SVG exports/new manifest | NOT CREATED. Earlier three captured baselines remain immutable. |
| Live Supabase/Vercel/Oracle | NOT DEPLOYED or smoke tested; user credentials/hostnames are required. |
| Live OpenRouter inference | No successful live call established in this increment. |

The user requested no further desktop-control testing. This checkpoint does not claim a completed manual customer/support/admin audit. See [handoff](handoff.md) for known unfinished behavior.
