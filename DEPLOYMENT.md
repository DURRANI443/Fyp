# Deployment guide

The versioned deployment guide is [doc/v0.3.0/deployment.md](doc/v0.3.0/deployment.md).

It covers **Supabase PostgreSQL**, **Vercel frontend**, and **Oracle Cloud backend**, with configuration templates, account provisioning, HTTPS, migrations, updates, backups, and verification. This file is the stable entry point; SDLC history stays in `doc/`.

Cloud deployment needs your provider accounts, selected free-tier resources, backend DNS hostname, and private credentials. No live cloud resources or live payments are created by this repository. The checked-in Vercel configuration deliberately refuses deployment until its example backend hostname is replaced.

Follow this order:

1. Create a free Supabase project and disable its Data API. Copy the Session pooler connection details and download the CA certificate.
2. Create an eligible Oracle Ubuntu VM and point a hostname at its public IP.
3. Follow the guide to install the backend, fill the private `.env`, migrate PostgreSQL, and create customer/support/admin accounts with your passwords.
4. Enable the supplied systemd service and Caddy HTTPS configuration. Verify the public backend health URL.
5. Run `python scripts/configure_vercel.py https://YOUR_BACKEND_HOST`, commit that public hostname, and import this GitHub repository into Vercel with Root Directory `frontend`.
6. Set the exact Vercel origin on Oracle and complete the guide's deployed login, checkout, role, and persistence checks.

The app works in offline mode throughout setup. Add an OpenRouter key only to Oracle's private environment when you want to enable the reviewed free model route. The backend and frontend require no Supabase browser API key or real payment provider.
