# Setup and demonstration

## Prerequisites and installation

Reference environment: Windows, Python 3.13, Node 24, npm, and an existing computer with internet for package/model installation. Docker, hosted workflow services and paid hosting are not required. Application data stays under the ignored `.local/` directory by default.

From the project root:

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1
```

Open http://127.0.0.1:8000 after the terminal reports application startup complete. A cached neural embedding model is warmed before the app accepts requests; the first measured load on this computer took about a minute. `Ctrl+C` stops the server. Setup installs pinned core dependencies, preserves an existing `.env`, builds the frontend, runs Alembic migrations and seeds missing demo data. Stop Vite and frontend test processes before setup: Windows locks native Node modules while they are running. Repeating setup or start does not reset orders or conversations. If local scripts are blocked, invoke `powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1`; this changes only that process's policy.

For local neural embeddings, run `scripts/setup.ps1 -WithEmbeddings`. This adds CPU PyTorch, Sentence Transformers and a pinned MiniLM model download. Without the model, retrieval explicitly reports TF-IDF fallback; the classifier and all workflows still run locally. Model installation is separate from OpenRouter generation.

For frontend development, run the backend as above and `npm run dev` inside `frontend/`; Vite proxies `/api` to port 8000. Changes to Python are visible after a server restart (or explicitly use Uvicorn `--reload` while developing). Run `npm run build` after frontend changes to refresh the application served on 8000.

## Demo accounts

All four synthetic accounts use password `DemoPass123!`:

| Role | Email | Purpose |
| --- | --- | --- |
| Customer | customer@demo.local | Main demonstration |
| Customer | other@demo.local | Separate ownership boundary |
| Support | support@demo.local | Claim and handle team tickets |
| Admin | admin@demo.local | Policies, staff teams, availability, audits |

The seed has processing order NS-1042, shipped/delayed NS-1038, recently delivered NS-1024 and an old delivery NS-1001. Dates are generated relative to the first seed time, so return eligibility changes as time passes. NS-2001 belongs to the other customer and must remain inaccessible to the main customer.

## Presentation walkthrough

1. Sign in as customer. Browse products, then orders. Ask “Where is order NS-1038?” and verify the answer against the order details.
2. In a new conversation ask “What is your return policy?” Inspect the approved policy citation. The reply is labelled local unless a live model actually succeeds.
3. Select cancellation for NS-1042. Inspect the proposal and confirm it. Refresh the order; it is cancelled. Repeated confirmation cannot create a second action.
4. Request a return for an item in NS-1024, enter a reason, and confirm. This requests staff review; it does not transfer money.
5. Ask for a person in a separate chat. Automated replies pause when queued. Sign out, sign in as staff, claim the ticket and reply. Sign back in as customer to inspect the staff reply.
6. As staff, review the return request and resolve a ticket with an outcome. Choose whether to hand the conversation back to the assistant.
7. As admin, create a new policy draft. It must not replace the active policy until approved. Inspect audit entries and staff availability.
8. Explain the AI evaluation and its limitations using [ai-evaluation.md](ai-evaluation.md); do not represent the small synthetic benchmark as real customer performance.

## Add your OpenRouter key

Edit the ignored root `.env` locally. Never place the key in chat, screenshots, Git, frontend source, or `VITE_*` variables.

```dotenv
LLM_MODE=openrouter
OPENROUTER_API_KEY=your-key-entered-locally
OPENROUTER_MODEL=google/gemma-4-31b-it:free
```

Restart the server. From `backend/`, run the separate synthetic live check:

```powershell
../.venv/Scripts/python.exe scripts/ai_smoke.py --live
```

This command uses one deliberately synthetic policy question and does not print the key or response body. A missing key, quota failure, unavailable free route, provider policy mismatch or failed validation is reported as not-run/failure, not a successful model call. The normal test suite uses no real API key. The adapter permits only the reviewed model, checks fresh zero prices, sets zero provider price caps, and has no paid fallback. See [AI design](ai-design.md) for exact guards and external sources. Set `LLM_MODE=offline` to return to local mode.

## Verification commands

From `backend/`:

```powershell
../.venv/Scripts/python.exe -m pytest tests -q
../.venv/Scripts/python.exe scripts/evaluate.py --output ../.local/intent-evaluation.json
../.venv/Scripts/python.exe scripts/ai_smoke.py --output ../.local/ai-smoke.json
```

From `frontend/`:

```powershell
npm test
npm run build
npm run test:e2e
```

Playwright needs Chromium. Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` if using an existing installation, or run `npx playwright install chromium` once. Browser tests use isolated synthetic databases and port 8001; they do not modify `.local/northstar.db`.

From the root, run `.venv/Scripts/python.exe scripts/check_docs.py`. Diagram rendering additionally requires root `npm ci` and an installed Chromium path in `PUPPETEER_EXECUTABLE_PATH`, then `npm run docs:render -- v0.2.0 .local/diagram-check/v0.2.0`. Captured baselines cannot be overwritten.

## Database options and data preservation

Leave `DATABASE_URL` blank for SQLite. For an existing local PostgreSQL installation, create a dedicated database and set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/DATABASE`, then run the same bootstrap/start command. Use a local account with access only to this database. Keep credentials in `.env`.

Switching database URLs does not copy old data. For a fresh demonstration, choose a new SQLite filename or a new PostgreSQL database and bootstrap it; retain the old database for recovery. Shut down the app before copying a SQLite database. PostgreSQL backup/restore uses its native tools. The optional PostgreSQL verification status is recorded in [verification.md](verification.md).

## Limits

The application is a single-process local FYP demo with shared synthetic passwords, in-memory rate limits, manual staff availability, and no payment gateway or real shop connector. It does not include password reset, customer registration, email/WhatsApp delivery, or public hosting. Local API documentation is available at http://127.0.0.1:8000/docs. Review the [traceability record](requirements-traceability.md) before claiming the complete original specification is delivered.
