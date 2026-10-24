# E-commerce AI Support FYP

A custom final-year project for customer support, knowledge-grounded answers, order assistance, and explainable ticket routing.

## Current status

**v0.3.0 is an unfinished development checkpoint**, saved at the user's request before final integration checks. See [the handoff note](doc/v0.3.0/handoff.md) for exact remaining work. Its source adds a photographed demonstration catalog, size selection, cart, approved/declined simulated payments and order receipts to the existing support portal. Product prices, inventory, shipping and customers are demo data. No actual payment or delivery occurs.

Deployment configuration is included for **Supabase PostgreSQL + Vercel frontend + Oracle backend**. Those services still require your accounts and deployment configuration. The optional OpenRouter adapter requires your backend API key and a currently available reviewed free endpoint.

- [Project instructions](agent.md)
- [Documentation index and version rules](doc/README.md)
- [Initial baseline](doc/v0.1.0/README.md)
- [Implementation milestone](doc/v0.2.0/README.md)
- [Session-switch fix and regression evidence](doc/v0.2.1/README.md)
- [Catalog, checkout, and hosting milestone](doc/v0.3.0/README.md)
- [Deployment instructions](DEPLOYMENT.md)
- [Setup and demonstration guide](doc/v0.2.0/runbook.md)
- [Verification and limitations](doc/v0.2.0/verification.md)
- [Technology, licenses, and cost assumptions](doc/v0.1.0/architecture/technology-stack.md)

## Run locally on Windows

Use Python 3.13 and Node 24. From this directory:

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1
```

Open **http://127.0.0.1:8000**. Setup is already complete in the current workspace; use the start command to run it again. If your PowerShell execution policy blocks local scripts, run `powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1` for that process only.

| Demo role | Email | Password |
| --- | --- | --- |
| Customer | customer@demo.local | DemoPass123! |
| Staff | support@demo.local | DemoPass123! |
| Administrator | admin@demo.local | DemoPass123! |

These accounts contain synthetic data. No real payment or refund transfer is performed. The [runbook](doc/v0.2.0/runbook.md) includes optional local embeddings, OpenRouter setup, tests, and a presentation walkthrough.

Tabs in the same browser profile share one sign-in. Logging in or out in one tab clears the previous workspace in the other tabs. For a simultaneous customer/staff demonstration, use separate browser profiles or a normal window plus an incognito window.

To update an existing local checkout, stop its server, run `npm --prefix frontend run build`, then run `scripts/start.ps1` and refresh portal tabs. Startup applies the additive migration and reference catalog update while preserving accounts, existing inventory, orders, and conversations. A new checkout reserves stock; cancelling that checkout restores it once. Original seeded orders remain demo fixtures.

For a purchase walkthrough: sign in as Customer, choose a product size, add it to the cart, review checkout, use fictional shipping details, and choose a simulated approval or decline. Approved purchases appear in My Orders and can use the existing support/cancellation flows. A decline creates no order. No payment-card details are requested.

## Technology direction

React + TypeScript + Vite; Python + FastAPI; SQLAlchemy + Alembic; SQLite by default with optional PostgreSQL; scikit-learn intent classification; local Sentence Transformers retrieval with an explicit TF-IDF fallback; and an OpenRouter adapter for optional grounded generation. The initial pgvector design is deferred; this small demo caches vectors locally in process.

All required local application components use open-source licenses. OpenRouter and the user-selected Supabase, Vercel, and Oracle hosting services are managed-service exceptions. No paid subscription or hosting is required for the reference local demonstration, which assumes an existing computer, electricity, and internet. Free hosted services have quotas, eligibility rules, and availability limits; see the deployment guide before creating cloud resources.

## Verification

Run backend tests from `backend/` using `../.venv/Scripts/python.exe -m pytest tests -q`. Run `npm test`, `npm run build`, and `npm run test:e2e` from `frontend/`. Browser tests create their own synthetic database. Detailed commands, measured AI results, and unresolved acceptance criteria are recorded in the milestone documents.

## Documentation verification

With Python installed, run from the repository root:

```powershell
python scripts/check_docs.py
```

This checks local Markdown links and captured-baseline hashes. It does not run application tests or prove that a Mermaid diagram renders correctly. Diagram rendering is recorded separately in the baseline verification report.

## Secrets and source history

Keep local secrets in ignored `.env` files. [`.env.example`](.env.example) documents configuration. Leave `LLM_MODE=offline` until your key is installed. Never put a key in frontend code or a `VITE_*` variable. The requested source destination is [DURRANI443/Fyp](https://github.com/DURRANI443/Fyp). Deployment account passwords are chosen through the backend operator command; the public demo password is rejected in production.

Project-authored code and documentation are licensed under [MIT](LICENSE). Dependencies and model artifacts retain their own licenses.
