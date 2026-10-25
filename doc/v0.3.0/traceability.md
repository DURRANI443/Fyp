# Requirement-to-verification mapping

| Requirement | Evidence |
| --- | --- |
| CAT-01 | `test_reference_refresh_does_not_reset_inventory_or_create_accounts`; existing-data SQLite migration check; photographed asset requests in `frontend/e2e/checkout.spec.ts`; [credits](../../frontend/public/products/credits.html). |
| BUY-01 | `checkout.test.tsx` size/quantity/stock checks and background purchase regression; customer-scoped session storage; mobile purchase browser workflow. |
| BUY-02 | `test_checkout_quote_and_receipt_use_database_prices`, `test_stale_price_requires_new_confirmation_without_mutation`; frontend quote invalidation and conflict tests. |
| PAY-01 | `test_declined_checkout_retains_stock_and_has_no_order`; approval/decline Vitest and mobile browser workflow. |
| PAY-02 | Checkout transaction tests, stock rollback and concurrent last-item purchase tests, on both SQLite and PostgreSQL. |
| PAY-03 | Backend duplicate/conflicting key tests and concurrent same-key requests; saved-payload retry and duplicate background response frontend tests. |
| BUY-03 | Purchase → persistent order → order question → confirmed cancellation/restock/refund browser workflow, plus backend checkout support tests. |
| DEP-01 | Both PostgreSQL migrations, `alembic check`, and all 95 backend tests passed locally against PostgreSQL 17.11. Actual Supabase endpoint still requires owner setup. |
| DEP-02 | Production build, rewrite preflight validation, same-origin API helper, [deployment runbook](deployment.md). Actual Vercel proxy/cookie smoke checks await hosting. |
| DEP-03 | ARM wheel-resolution dry-run, Caddy/systemd templates and documented operations. Real VM execution, DNS and HTTPS await hosting. |
| DEP-04 | `test_deployment.py` production guards, configured host, prompted provisioning and password-reset session invalidation. |
| REL-01 | Versioned documents, three rendered diagrams, captured manifest and local link/hash checks. GitHub contains source, not private configuration or local databases. |

The test commands and observed totals are in [verification](verification.md). These links distinguish local validation from external integration still requiring accounts.
