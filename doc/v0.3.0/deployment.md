# Supabase, Vercel, and Oracle deployment

Version: v0.3.0. Prepared: 2026-10-24. Scope: a private, small FYP demonstration with simulated commerce. **Configuration and local checks are implemented; live cloud deployment has not been performed.** Provider accounts, a backend hostname, and credentials must be supplied by the project owner.

## Architecture and free-tier boundary

The browser loads the React bundle from Vercel and calls relative `/api/...` URLs on that same Vercel origin. Vercel forwards those requests to an Oracle HTTPS endpoint. Caddy terminates TLS on the VM and forwards API traffic to Uvicorn on `127.0.0.1:8000`. Only the Python backend connects to Supabase PostgreSQL. OpenRouter remains optional and backend-only.

This arrangement keeps session cookies first-party: HttpOnly, Secure, SameSite=Lax, with the existing CSRF header. Do not replace the frontend API helper with a direct cross-site backend URL. The selected managed hosting services are user-authorized exceptions to self-hosting; their free tiers are services, not an assertion that all provider infrastructure is open-source.

Use Vercel **Hobby** for this personal, non-commercial FYP. Usage limits still apply. Do not select a Pro trial or paid add-ons to complete this guide. [Vercel Hobby terms](https://vercel.com/docs/plans/hobby).

At the time checked, Oracle documents an A1 Always Free allowance equivalent to **2 OCPUs and 12 GB memory**, plus shared storage allowances; account-wide usage counts. Older tutorials often quote different limits. Select only resources marked eligible in your own home-region Console, check the displayed estimate before creation, and stay inside the account's allocation. Capacity can be unavailable and idle VMs may be reclaimed. Do not upgrade to paid resources to work around availability. [Oracle Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

## 1. Prepare the required values

| Value | Location and purpose |
| --- | --- |
| Git repository | `https://github.com/DURRANI443/Fyp.git` |
| Supabase database connection | Dashboard **Connect → Session pooler**, PostgreSQL password and CA certificate |
| Oracle VM | Ubuntu 24.04 LTS, eligible A1 shape, public IP, SSH key |
| Backend DNS name | A hostname pointing to that public IP; use an existing domain or a free DNS subdomain |
| Vercel production origin | Exact `https://YOUR_PROJECT.vercel.app` shown by Vercel, or your configured custom domain |
| Application accounts | Separate customer, support, and admin email/password combinations you choose |
| Optional OpenRouter key | Keep only in the backend `.env`; never Git or `VITE_*` |

A domain purchase is unnecessary if you use a free DNS provider such as [Duck DNS](https://www.duckdns.org/about.jsp). Create your own hostname, point it to the Oracle IP, and keep any DNS account token private. Recheck DNS after an IP change. Do not use someone else's hostname or an example hostname from this guide.

## 2. Configure Supabase

1. Create a Free project. Keep its database password in your password manager.
2. **Disable the Data API before creating application tables:** Dashboard → Integrations → Data API → turn **Enable Data API** off. This project uses its own session authentication and SQLAlchemy; it does not use Supabase Auth or Supabase REST clients. Exposing these tables through a separate Data API would bypass this application's ownership checks unless separately designed RLS policies were added. Keep the Data API disabled. [Supabase API security](https://supabase.com/docs/guides/api/securing-your-api).
3. Open **Connect → Session pooler**. Copy its real host, username, database name and port; use port **5432** for session mode. The IPv4-compatible session pooler avoids buying an IPv4 add-on. Do not switch this long-running backend to transaction mode on 6543: transaction mode has additional prepared-statement restrictions. [Connection modes](https://supabase.com/docs/guides/database/connecting-to-postgres).
4. Enable database SSL enforcement where available and download the project's CA certificate from Database Settings → SSL Configuration. Copy it to the Oracle VM as `/opt/northstar/certs/supabase-ca.crt`. Use `sslmode=verify-full` and the matching `sslrootcert` path. [Supabase SSL modes](https://supabase.com/docs/guides/platform/ssl-enforcement).
5. Use the SQLAlchemy driver prefix `postgresql+psycopg://`. Percent-encode special characters in the password **once** before placing it in the URI. Do not paste a database URI into chat, a screenshot, Git, or the frontend.

The backend template has the format below. Every uppercase placeholder must be replaced:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:URL_ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=verify-full&sslrootcert=/opt/northstar/certs/supabase-ca.crt
```

No Supabase publishable key, service-role key, JavaScript SDK, pgvector extension, or public RLS policy is required for this deployment. Application migrations create ordinary PostgreSQL tables. Start with a new project; migrating existing SQLite business data is a separate export/import task, not part of schema migration.

## 3. Create the Oracle VM and networking

Use an eligible Ubuntu 24.04 A1 instance with a practical starting allocation of **1 OCPU / 6 GB RAM** and a boot volume inside your remaining free storage allowance. The CPU-light application profile below does not install PyTorch. A1 availability and exact eligible shapes are controlled by Oracle, not this repository.

Use a public subnet with an internet gateway and a route for `0.0.0.0/0`. In the VM's network security group or subnet security list allow TCP 22 **only from your own IP**, and TCP 80/443 from internet clients. Keep port 8000 closed externally; PostgreSQL is hosted by Supabase, so do not open 5432 on the VM. Allow the outbound connections needed for package downloads, DNS, certificate issuance, Supabase, and optional OpenRouter.

Connect with the SSH private key you saved when creating the VM:

```bash
ssh -i /path/to/your-private-key ubuntu@YOUR_ORACLE_IP
```

Commands below run in the Oracle Ubuntu SSH terminal, unless labelled otherwise. They are an installation runbook, not evidence that this VM has been provisioned.

```bash
sudo apt update
sudo apt install -y git curl ca-certificates python3-venv nano
sudo useradd --system --user-group --home-dir /opt/northstar --shell /usr/sbin/nologin northstar
sudo git clone https://github.com/DURRANI443/Fyp.git /opt/northstar
sudo chown -R northstar:northstar /opt/northstar
sudo -Hu northstar mkdir -p /opt/northstar/.local /opt/northstar/certs
sudo -Hu northstar python3 -m venv /opt/northstar/.uv
sudo -Hu northstar /opt/northstar/.uv/bin/python -m pip install uv
sudo -Hu northstar env UV_PYTHON_INSTALL_DIR=/opt/northstar/.python /opt/northstar/.uv/bin/uv python install 3.13
sudo -Hu northstar env UV_PYTHON_INSTALL_DIR=/opt/northstar/.python /opt/northstar/.uv/bin/uv venv --python 3.13 /opt/northstar/.venv
sudo -Hu northstar /opt/northstar/.uv/bin/uv pip install --python /opt/northstar/.venv/bin/python -r /opt/northstar/backend/requirements.txt
```

Skip `useradd`/`git clone` if you are updating an existing installation. Do not replace the system Python. `uv` manages the separate Python 3.13 runtime inside the application directory. The app's dependencies are pinned; record `uv --version` and the installed Python patch version in your deployment notes. [uv Python management](https://docs.astral.sh/uv/guides/install-python/).

If the VM image has an active OS firewall, permit TCP 80/443 there too without deleting existing rules. If you use UFW, first allow SSH from your IP, then HTTP/HTTPS, and verify access in a second SSH session before enabling it. Oracle network rules and the VM firewall are separate layers.

## 4. Set private environment configuration and initialize data

```bash
sudo -Hu northstar cp /opt/northstar/deploy/oracle/.env.example /opt/northstar/.env
sudo chmod 600 /opt/northstar/.env
sudo -Hu northstar nano /opt/northstar/.env
```

Use your editor if `nano` is unavailable. Replace the database URI, exact Vercel HTTPS origin, and backend hostname. Preserve these deployment settings:

```dotenv
APP_ENV=production
SEED_DEMO=false
SECURE_COOKIES=true
ALLOWED_ORIGINS=https://YOUR_PROJECT.vercel.app
TRUSTED_HOSTS=YOUR_BACKEND_HOST,localhost,127.0.0.1
EMBEDDING_MODE=tfidf
LLM_MODE=offline
```

There is no slash at the end of an origin. Hosts contain no protocol, port, or path. If you later add a custom frontend domain, append its exact HTTPS origin as a comma-separated value. Do not allow `*.vercel.app` or arbitrary preview deployments. A preview that must access this database needs an explicitly reviewed origin, or preferably its own database/backend.

Copy the Supabase CA certificate you downloaded into the `certs` directory and make it readable by `northstar`. Then run migrations, seed reference products/policies, and create your accounts:

```bash
cd /opt/northstar/backend
sudo -Hu northstar /opt/northstar/.venv/bin/python -m app.bootstrap
sudo -Hu northstar /opt/northstar/.venv/bin/python -m app.catalog
sudo -Hu northstar /opt/northstar/.venv/bin/python -m app.manage_users create --email admin@example.org --name "Store Admin" --role admin --teams logistics,returns,billing,general
sudo -Hu northstar /opt/northstar/.venv/bin/python -m app.manage_users create --email support@example.org --name "Support Operator" --role support --teams logistics,returns,billing,general
sudo -Hu northstar /opt/northstar/.venv/bin/python -m app.manage_users create --email customer@example.org --name "Demo Customer" --role customer
sudo -Hu northstar /opt/northstar/.venv/bin/python -m app.manage_users check
```

Replace those example emails/names with the demo accounts you want to use. Passwords are entered using hidden prompts, must be at least 14 characters, and are not printed or passed as command-line arguments. There is no public registration/password-reset email flow in this FYP. `SEED_DEMO=false` prevents shared default accounts; reference-data initialization does not create users or historical orders. A new customer purchases through the simulated checkout to create an order.

If you imported a database containing the four original `@demo.local` accounts, reset each account's password before starting production. The backend refuses to start while any of those accounts still uses the published default password. To reset any account and revoke its active sessions:

```bash
sudo -Hu northstar /opt/northstar/.venv/bin/python -m app.manage_users reset-password --email customer@example.org
```

## 5. Start the backend with systemd

```bash
sudo cp /opt/northstar/deploy/oracle/northstar.service /etc/systemd/system/northstar.service
sudo systemctl daemon-reload
sudo systemctl enable --now northstar
sudo systemctl status northstar --no-pager
curl --fail http://127.0.0.1:8000/api/health
```

Expected health JSON includes `"status":"ok"` and `"database":"postgresql"`. `sqlite` means the wrong configuration is loaded. The service reads `/opt/northstar/.env` through Pydantic; it does not require exporting the URI into shell history. It binds only to loopback and trusts proxy headers only from local Caddy. Keep a single worker: the demo rate limiter and AI caches are in process. Multiple workers need a shared limiter and an explicit resource review.

If startup fails, inspect `sudo journalctl -u northstar -n 80 --no-pager`. Do not post unsanitized logs containing database connection errors. Production settings fail closed for insecure cookies, demo seeding, wildcard hosts/origins, or a missing PostgreSQL TLS mode.

## 6. Add HTTPS with Caddy

Point your backend hostname's DNS A record to the Oracle public IP first. Install Caddy using its stable Ubuntu package repository. The package sets up the `caddy` systemd service. [Official installation instructions](https://caddyserver.com/docs/install#debian-ubuntu-raspbian).

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https gpg
curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key -o /tmp/caddy-signing.key
sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg /tmp/caddy-signing.key
curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt -o /tmp/caddy-stable.list
sudo install -m 644 /tmp/caddy-stable.list /etc/apt/sources.list.d/caddy-stable.list
sudo chmod 644 /usr/share/keyrings/caddy-stable-archive-keyring.gpg
sudo apt update
sudo apt install -y caddy
sudo cp /opt/northstar/deploy/oracle/Caddyfile /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile
```

Replace `YOUR_BACKEND_HOST` with your real DNS name, without `https://`. Then validate and reload:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
curl --fail https://YOUR_BACKEND_HOST/api/health
```

Caddy obtains and renews a public certificate for a publicly resolvable DNS name when ACME challenges can reach the VM. Both cloud and local firewall settings must permit the required traffic. Do not use `curl -k` or an insecure HTTP proxy destination to hide a certificate failure. [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).

## 7. Connect Vercel to GitHub

On your development computer, from the repository root, configure the real public backend hostname and commit the generated routing change:

```powershell
.\.venv\Scripts\python.exe scripts/configure_vercel.py https://YOUR_BACKEND_HOST
git add frontend/vercel.json
git commit -m "Configure Oracle API origin for Vercel"
git push origin main
```

The hostname is public configuration, not a secret. `frontend/vercel.json` ships with an intentionally invalid placeholder, and its Vercel-only preflight rejects that placeholder. Ordinary local `npm run build` still works before hosting is configured.

In Vercel, import `DURRANI443/Fyp`, select Hobby, and set:

| Setting | Value |
| --- | --- |
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Node.js version | 24.x |
| Install | `npm ci` (from `vercel.json`) |
| Build | `node scripts/check-deployment.mjs && npm run build` |
| Output | `dist` |
| Backend secrets in Vercel | None |

The `/api/:path*` rule forwards the complete API path to Oracle. API responses explicitly disable CDN caching. The SPA fallback excludes `/api`, so API failures remain API failures. This is an external rewrite, not a redirect; the frontend keeps its own URL and cookies. [Vercel rewrites](https://vercel.com/docs/routing/rewrites), [Vite deployment](https://vercel.com/docs/frameworks/frontend/vite).

Copy Vercel's actual production origin into Oracle `ALLOWED_ORIGINS`, restart `northstar`, and verify the public site. Never add `DATABASE_URL`, the OpenRouter key, or private passwords as `VITE_*` values: Vite variables are compiled into the browser bundle. Backend credentials remain solely on Oracle.

## 8. Verify the deployed system

These checks are **pending until your cloud resources exist**. Record actual dates/results in a new documentation increment instead of claiming this runbook as a successful deployment.

1. Open `https://YOUR_PROJECT.vercel.app/api/health`. Confirm PostgreSQL and the release version. Check `/api/system` shows `demo_accounts_enabled: false`.
2. Log in with your provisioned customer. Inspect the response cookie: Secure, HttpOnly, SameSite=Lax, host-only, path `/`. Refresh and confirm the session remains active. Log out and confirm authenticated endpoints return 401.
3. Add an item, review the quote, simulate decline, then simulate approval. Verify the decline creates no order, approval creates one owned order, and stock changes once. Reload the receipt/order page and verify persistence.
4. Ask about the new order, request a person, then switch to the support account. Claim, reply, and resolve the ticket. Reopen as customer to read the response. No stale customer conversation polling should occur after role changes.
5. Log in as admin; inspect knowledge, teams, and audit events. Confirm customer/support accounts cannot access admin endpoints.
6. Inspect API responses for `Cache-Control: no-store`. Verify a request with an unapproved Origin is rejected on writes and a write without CSRF is rejected while logged in.
7. Restart `northstar`, repeat health/login/order retrieval, and verify no default users were recreated. Keep the Supabase Data API disabled.

## 9. Optional AI inference

The initial Oracle profile uses TF-IDF retrieval plus the existing local intent classifier; it is a functional CPU-light fallback. It is not a claim that MiniLM is running. With `LLM_MODE=offline`, responses are explicitly labelled local/offline.

To enable the already-reviewed free OpenRouter route, put your key in Oracle `.env`, set `LLM_MODE=openrouter`, and run from `backend`:

```bash
sudo -Hu northstar /opt/northstar/.venv/bin/python scripts/ai_smoke.py --live
sudo systemctl restart northstar
```

That explicit check sends only a synthetic policy question. The adapter rejects unavailable/nonzero-priced routes and has no paid fallback. A configured key alone is not evidence of a successful live answer. Never add credits or select a paid model as an automatic fix.

Optional sentence-transformer dependencies are kept in `backend/requirements-ai.txt`; those exact CPU wheels were tested locally on Windows, not on Oracle ARM. Do not assume the `+cpu` wheel pins support A1. Keep TF-IDF on A1 until an ARM-specific dependency lock and smoke test have been validated in a later increment. All ownership, checkout, policy, and handoff decisions remain server-side regardless of AI mode.

## 10. Updates, backups, and troubleshooting

Before an update, save a database backup and record the current Git revision. Free Supabase projects should export their data regularly; do not assume paid-plan automatic backup retention is included. Keep a copy outside the Oracle VM because the VM can be reclaimed. [Supabase backup guidance](https://supabase.com/docs/guides/platform/backups).

Use a PostgreSQL `pg_dump` client compatible with the server version and a private `.pgpass`/connection service file, or Supabase's documented export workflow. Never put the password on the command line. Restore a backup to a separate disposable project first, keep that project's Data API disabled, and verify counts/orders before treating the backup as usable. An application Git rollback does not roll back database migrations.

For a reviewed application update:

```bash
sudo systemctl stop northstar
sudo -Hu northstar git -C /opt/northstar pull --ff-only
sudo -Hu northstar /opt/northstar/.uv/bin/uv pip install --python /opt/northstar/.venv/bin/python -r /opt/northstar/backend/requirements.txt
cd /opt/northstar/backend
sudo -Hu northstar /opt/northstar/.venv/bin/python -m app.bootstrap
sudo -Hu northstar /opt/northstar/.venv/bin/python -m app.catalog
sudo systemctl start northstar
curl --fail https://YOUR_BACKEND_HOST/api/health
```

Vercel rebuilds on Git pushes. Apply backward-compatible API/schema changes first, then deploy the frontend. For a migration that is not backward-compatible, plan a maintenance window and tested restore procedure. Do not run an automatic destructive downgrade.

| Symptom | Check |
| --- | --- |
| Vercel preflight stops | Run `scripts/configure_vercel.py` with your real Oracle HTTPS origin and commit the result |
| 502 / timeout from Vercel | Check Oracle service, Caddy certificate, DNS, public 80/443 rules, and direct backend health |
| `Invalid host header` | Add the actual Oracle backend hostname to `TRUSTED_HOSTS`, then restart |
| Login works but writes return 403 | Exact browser origin in `ALLOWED_ORIGINS`; current CSRF header; no cross-site frontend API URL |
| Login disappears on refresh | Check Secure cookie on HTTPS and same-origin `/api` proxy; API caching must stay disabled |
| Supabase connection failure | Project active, correct Session pooler host/user/5432, encoded password, CA file and TLS mode |
| Empty knowledge/products | Run `python -m app.catalog` against the same database as the service |
| Production refuses startup | Resolve the named configuration problem or rotate old demo passwords; do not disable the guard |
| Model fails on A1 | Keep `EMBEDDING_MODE=tfidf`; validate ARM wheels separately |
| Occasional 429 | Single-process demo limiter, plus provider quotas; wait/retry without increasing paid service limits |

No real card numbers, CVVs, bank accounts, refunds, deliveries, tax filings, or payment gateway are involved in this FYP. The deployed purchase flow remains clearly simulated.
