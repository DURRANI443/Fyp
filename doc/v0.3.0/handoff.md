# Deployment handoff

Updated: 2026-10-25 (Asia/Karachi). The unfinished `7f779ef` checkpoint has been completed and verified locally. The remaining steps are provider/account setup, because the owner confirmed that no Supabase, Vercel or Oracle resources exist yet.

## Completed checkpoint items

- Fixed in-flight checkout clearing later additions; duplicate responses settle cart quantities once.
- Included all ten local product photos with [source/license credits](../../frontend/public/products/credits.html).
- Aligned frontend and documentation tool package versions at 0.3.0; production build succeeds.
- All eight browser workflows pass, including the new purchase and decline flows.
- PostgreSQL migrations, schema check and all 95 backend tests pass; the 46 core pins resolve for Python 3.13/Linux ARM.
- Completed requirements, API contract, diagrams, traceability, actual evidence and baseline capture.

See [verification](verification.md) for measured results. No unresolved application defect was observed by those checks; cloud behavior remains unverified until actual deployment.

## What the owner supplies for hosting

1. A free Supabase project, its Session pooler details/password and CA certificate; disable its Data API.
2. An eligible Oracle Ubuntu VM, SSH access and a DNS hostname pointing to its public IP.
3. A Vercel Hobby project imported from [DURRANI443/Fyp](https://github.com/DURRANI443/Fyp), Root Directory `frontend`.
4. Chosen customer, support and admin account passwords, entered through the backend provisioning prompts.
5. Optional OpenRouter key stored only in Oracle's private `.env`.

Follow [DEPLOYMENT.md](../../DEPLOYMENT.md) and the [full runbook](deployment.md) in order. Keep secrets out of Git and chat. Configure the real backend destination before importing/building on Vercel; its current `.invalid` placeholder intentionally fails the deployment preflight.

Record live hosting verification in the next documentation increment rather than editing this captured local baseline. Continue using automated checks; the user requested no GPTcontrol/desktop automation.
