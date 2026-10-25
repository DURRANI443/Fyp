# v0.3.0 verification

Completed: 2026-10-25 (Asia/Karachi). Scope: application implementation, local integrations and deployment preparation. The owner confirmed that cloud resources have not been created, so no live Supabase/Vercel/Oracle result is claimed.

| Check | Observed result |
| --- | --- |
| SQLite backend: `pytest tests -q` | **95 passed**, 32.82 s. Includes checkout/stock/concurrency, auth/CSRF/ownership, customer/staff/admin workflows, AI fallback and deployment/account guards. |
| PostgreSQL backend: same suite with `TEST_POSTGRES_URL` | **95 passed**, 313.88 s against local PostgreSQL 17.11. Tests create/drop isolated schemas, including concurrent same-key and last-item purchases. |
| PostgreSQL migration and schema | Both migrations applied to a fresh dedicated database. `alembic check`: no new upgrade operations. Reference data: 4 users, 10 products, 5 seed orders and 8 policy documents; revision `91bb428af032`. |
| Existing SQLite data upgrade | Earlier backup migration preserved 4 users, 5 orders, 7 items, 5 conversations and 4 tickets. Foreign-key check clear; reference refresh preserves changed prices/stock and does not recreate accounts. |
| Current local demo upgrade | Backed up and migrated the user's local database on 2026-10-25. Preserved 4 users, 5 orders, 7 items, 5 conversations, 21 messages and 4 tickets; catalog now has 10 products; foreign-key check clear. |
| Frontend: `npm test -- --reporter=dot` | **40 passed**, 37.57 s, including later cart additions surviving payment completion, duplicate background replies, exact retry payload recovery, quote invalidation and production login. |
| Frontend: `npm run build` | TypeScript and production Vite build passed. Bundle approximately 288 kB JS / 59 kB CSS before compression; all ten local product JPEGs are included. |
| Browser: `npm run test:e2e` | **8 passed**, 2.1 min in final clean run. See [browser log](evidence/browser-workflows.txt). Headless Chromium uses an isolated migrated SQLite database on port 8001. |
| Final privacy regression | **30 AI tests passed**, 3.34 s after extending redaction to new hexadecimal order references. This string-processing change is independent of database behavior. |
| ARM package availability | Cross-platform Python 3.13/Linux aarch64 pip dry-run resolved all **46** pinned core packages to wheels. No actual Oracle/ARM runtime was executed. [Resolution summary](evidence/arm-wheels.json). |
| Deployment configuration | Production settings/account tests passed within the backend suite. Invalid dev cookies/seeding/origins/hosts/non-TLS DB settings are rejected; reset-password revokes sessions. |
| Vercel configuration | Placeholder intentionally rejects deployment until `configure_vercel.py` sets a real HTTPS backend. Syntax/preflight checks do not prove live connectivity or proxy-cookie behavior. |
| Local start script | PowerShell parser reported no syntax errors. It builds by default; `-SkipBuild` is an explicit opt-out. |
| Frontend runtime dependency audit | `npm audit --omit=dev --audit-level=high --json` reported zero vulnerabilities. This is a point-in-time dependency check, not a general security certification. |
| Documentation | Three Mermaid sources rendered to SVG; checkout and deployment previews visually inspected, with no clipped labels. Local links and captured manifests checked before publication. |

## Browser coverage

1. Desktop purchase, selected size/quantity, all ten photo HTTP responses, persistent receipt/order, explicit order-status question, confirmed cancellation, stock restoration and simulated refund.
2. Mobile decline creates no order and keeps the cart; a fresh approved attempt creates exactly one order; no horizontal overflow.
3. Same-page customer to staff to customer role change stops stale polling and preserves staff replies.
4. Shared-tab role changes clear the previous workspace and stop unauthorized old requests.
5. Approved policy citations, human handoff, staff claim/reply/resolve, customer readback and resumed assistant.
6. Cancellation confirmation/back-out, return submission, staff approval and customer persistence.
7. Admin knowledge draft/approval, team availability persistence and audit/metrics.
8. Mobile order eligibility and grounded support without overflow.

The first integration attempts exposed outdated test selectors and the need to submit/edit the order-help prefill. They were corrected before the final eight-test pass. Generic help questions may intentionally route to a human; specific tracking questions use verified order facts.

## Evidence and limits

- [Validation summary](evidence/validation.json), [checkout receipt](evidence/checkout-receipt.png), [mobile checkout](evidence/checkout-mobile.png), [staff inbox](evidence/staff-inbox-desktop.png), [admin knowledge](evidence/admin-knowledge-desktop.png), and [catalog](evidence/customer-desktop.png).
- Cloud DNS/TLS, Supabase credentials, Vercel rewrites/cookies, real VM startup and cloud restarts remain the deployed smoke checks in [the runbook](deployment.md). These require the owner's new resources.
- No live OpenRouter key is configured. Offline mode is functional; successful live generation still needs the key and an available reviewed free route. No paid fallback exists.
- The Oracle profile uses TF-IDF and a local intent classifier. Optional pinned neural wheels were tested previously on Windows, not Oracle ARM.
- Classifier quality/unknown-intent limits remain those measured in [v0.2.0](../v0.2.0/verification.md); passing workflows do not establish general AI accuracy.
- No completed manual desktop-control audit is claimed. The user requested code-based verification.
- Transactions and rate limits suit a small single-worker FYP deployment. Registration, email recovery, real money, physical delivery and tax processing are outside this increment.
