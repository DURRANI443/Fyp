# Increment requirements

The original support/routing requirements continue to apply. These additions follow the user's request for proper products, fake payments, GitHub publication, and a Supabase/Vercel/Oracle setup guide.

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| CAT-01 | Realistic demonstration catalog | Useful descriptions, photographs with documented sources, demo prices, available sizes, and stock; existing order history survives the catalog update. |
| BUY-01 | Customer cart | Select a size, add/remove items, change quantity, and review the cart without leaking it across accounts. |
| BUY-02 | Server-priced review | Backend computes totals and validates products, sizes, and stock; stale price/stock conditions require review again. |
| PAY-01 | Explicit simulated payment | The customer can choose approval or decline without entering a card number, expiry, or CVV. Every outcome identifies the payment as simulated. |
| PAY-02 | Atomic purchase | Approval creates exactly one owned order and payment record, and reserves inventory in one database transaction. Declines create no order and reserve no stock. |
| PAY-03 | Retry safety | Same key and payload return the original result; changed payload with the same key is rejected. Concurrent purchases cannot oversell. |
| BUY-03 | Support integration | The new purchase is visible in My Orders and can enter existing order support/cancellation flows. Cancelling a purchased order restores stock once and records a simulated refund. |
| DEP-01 | Supabase PostgreSQL | Document TLS, password encoding, session pooler, migrations, account provisioning, and restricting database exposure. |
| DEP-02 | Vercel frontend | Build from the frontend directory and proxy /api to an explicitly configured HTTPS Oracle origin. No backend credentials enter frontend build variables. |
| DEP-03 | Oracle backend | Document VM capacity limits, Python environment, systemd, HTTPS, firewall, configuration, health checks, updates, and backups. |
| DEP-04 | Safe hosted accounts | Production rejects insecure default configuration and shared demo passwords. Provision accounts explicitly with chosen passwords. |
| REL-01 | Versioned delivery | Preserve v0.1.0–v0.2.1; capture new diagrams, changes, and actual verification here. Publish to the specified repository when authenticated write access is available. |

Non-goals: real payments/refunds, live merchant inventory/prices, shipping-label purchase, automated tax compliance, self-service registration or password recovery, and an asserted live cloud deployment without accounts and credentials.
