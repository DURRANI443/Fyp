# Change log

## Added

- Realistic product catalog with photographs, size selection, cart, and checkout review.
- Explicit approved/declined demo payment scenarios, owned order creation, stock reservations, idempotent results, and cancellation inventory restoration.
- Additive schema migration and reference-data refresh without resetting existing user data.
- Production settings, explicit account provisioning, Vercel proxy configuration, Oracle service/reverse-proxy templates, and Supabase connection guidance.
- Separate root deployment guide, new SDLC baseline/diagrams, and a GitHub Actions verification workflow.

## Fixed from the interrupted audit

- Return eligibility uses remaining quantities and excludes future delivery dates.
- Administrators cannot remove a team from a member with unresolved assigned tickets in that team.
- Whitespace-only knowledge submissions are rejected; intent metrics count classified customer turns.
- Customer conversation changes clear stale loading state and failed history does not permit wrong-thread replies.
- Staff selection follows active filters; team controls synchronize after refresh; administrator intervention is represented in the interface.
- Form limits match backend validation.

## Preserved

- Existing orders, conversations, role boundaries, shared-tab session invalidation, human handoff, and confirmation rules.
- Earlier documentation manifests and evidence, including their historical limitations.

See [verification](verification.md) for actual checks; source changes alone do not constitute a live deployment or a completed manual browser audit.
