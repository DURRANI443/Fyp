# Deployment guide

The versioned deployment guide is [doc/v0.3.0/deployment.md](doc/v0.3.0/deployment.md).

It covers **Supabase PostgreSQL**, **Vercel frontend**, and **Oracle Cloud backend**, with configuration templates, account provisioning, HTTPS, migrations, updates, backups, and verification. This file is the stable entry point; SDLC history stays in `doc/`.

Cloud deployment needs your provider accounts, selected free-tier resources, backend DNS hostname, and private credentials. No live cloud resources or live payments are created by this repository. The checked-in Vercel configuration deliberately refuses deployment until its example backend hostname is replaced.
