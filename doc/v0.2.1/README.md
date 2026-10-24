# v0.2.1 — Shared-browser session and polling fix

Status: **Captured patch documentation baseline**. Date: 2026-10-24, Asia/Karachi.
Predecessor: [v0.2.0](../v0.2.0/README.md), preserved unchanged.

## Report and reproduction

The user reported repeated customer conversation `404` responses after signing out as a customer and signing in as staff. Staff ticket lookup, claim and reply returned `200`. Reproduction against the previous production build established:

- Switching accounts in one live page already stopped the customer poll and preserved staff replies.
- Opening two tabs in the same browser context, leaving a customer handoff chat open, and changing the account in the other tab reproduced three repeated customer conversation `404`s while staff operations succeeded.

Browser tabs share the HTTP-only session cookie. The original customer screen retained its in-memory account and four-second poll after the other tab replaced that cookie with the staff session. The customer endpoint correctly rejected access to a conversation not owned by that authenticated user. The missing piece was frontend synchronization and request cleanup; authorization is unchanged.

The initial four browser tests used separate customer and staff browser contexts, with separate cookies. They exercised actual UI/API workflows but missed shared-cookie account switching. Passing them was not proof that this scenario or every real-user workflow worked. [Pre-fix network evidence](evidence/shared-tab-before-network.json) includes the expected unauthenticated `/auth/me` 401 separately from the three erroneous repeated conversation 404s. The pre-fix screenshots show [the stale customer page](evidence/shared-tab-before-1.png) and [the staff page](evidence/shared-tab-before-2.png).

## Changed behavior

Login/logout publishes a random, credential-free browser-storage marker. Other tabs immediately clear the old workspace, cancel pending requests, stop its polls, and show sign-in with an explanation. Normal initial session restoration is silent, so simply opening a second tab does not sign out the first.

Each API request is associated with the local session generation. Changing the session aborts pending requests and prevents a late success or 401 from restoring old data or signing out a newly logged-in account. Initial authentication restoration has a separate cancellation guard. Customer and staff polls now cancel on cleanup, avoid overlapping requests, and stop on terminal 401/403/404 responses. If browser storage is disabled, terminal polling failures still stop retries; cross-tab notifications depend on browser storage support.

No API permissions, schema, migrations, demo orders, tickets or existing conversations were reset by this patch. The implementation is in [session transport](../../frontend/src/api.ts), [application lifecycle](../../frontend/src/App.tsx), [customer polling](../../frontend/src/customer.tsx), and [staff polling](../../frontend/src/staff.tsx). The [sequence diagram](diagrams/session-change.svg) and [editable source](diagrams/session-change.mmd) describe the new lifecycle.

## Verification and traceability

See the [verification record](verification.md) for actual results. New tests cover session invalidation, stale responses, canceled bootstrap, terminal poll errors, overlapping requests, unmount cancellation, same-page switching and shared-cookie tabs. This patch strengthens FR-001 (authentication), FR-003 (conversation isolation), FR-011/FR-012 (handoff/staff continuity), and NFR-002/NFR-009 (security and regression coverage). No independent human acceptance test or live OpenRouter result is claimed.

## Apply the update

The production frontend has been rebuilt. Stop your current server with Ctrl+C, run `scripts/start.ps1` again, then hard-refresh **every open portal tab** with Ctrl+F5. Existing browser pages keep their already-loaded JavaScript until refreshed.

Use separate browser profiles, different browsers, or one normal window plus an incognito window to demonstrate customer and staff simultaneously with independent sign-ins. Tabs within one normal profile share one sign-in; this patch makes account changes explicit and removes the previous stale workspace.

Base setup and demo accounts remain in the [v0.2.0 runbook](../v0.2.0/runbook.md). No new dependency or API key is required for this fix.

## SDLC process

Reproduce the report on the old build; record a failing shared-tab regression and a passing single-page control; implement session/request lifecycle changes; verify unit, API and actual-browser behavior; rebuild; capture this patch baseline without altering older manifests. See [CHANGELOG](CHANGELOG.md).
