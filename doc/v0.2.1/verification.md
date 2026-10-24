# Verification

Date: 2026-10-24, Asia/Karachi. Final results for the captured patch.

| Check | Actual result | What it establishes |
| --- | --- | --- |
| Pre-fix same-page browser test | Passed, 14.1s | Ordinary logout/login in one mounted page already stopped its old poll |
| Pre-fix shared-cookie two-tab test | Failed, 18.6s | Reproduced the stale customer workspace and repeated 404 responses |
| Frontend unit/component tests | **20 passed**, 8.79s | Existing 11 plus nine session/request/polling regressions |
| TypeScript and production build | Passed | New frontend compiled and production assets rebuilt; test-only locator typing corrected |
| Core backend tests | **9 passed**, 1.77s | Authentication, ownership, CSRF, role and core API checks remain intact |
| Final browser suite | **6 passed**, 1.1 minutes | Original four workflows plus both new session-switch workflows; [captured output](evidence/browser-tests.txt) |
| Same-page role switch | Passed; 11,894ms observation window | Zero stale customer requests, zero API failures, ten successful staff responses; [network evidence](evidence/same-page-after-switch-network.json) |
| Shared-cookie tab switch | Passed; 11,929ms observation window | Old customer workspace removed, zero stale customer requests, zero API failures, ten successful staff responses; [network evidence](evidence/shared-tab-after-switch-network.json) |
| Session sequence diagram | Rendered successfully | Editable Mermaid source and SVG retained |

The [old customer tab after the fix](evidence/old-customer-tab-cleared.png) visibly shows the sign-in screen and account-change notice, without the previous conversation. The [new staff tab](evidence/new-staff-tab-replied.png) shows the saved staff reply. The isolated browser-test server stopped after execution; the user's running port-8000 server was left untouched. An original browser assertion was scoped to the current message bubble so new resolved-ticket previews could not match it ambiguously.

The full backend workflow/AI suites were not rerun for this frontend patch; the previous milestone records those executions. No database policy, routing or generation logic changed. OpenRouter live inference remains outside this patch's verification.

## Regression sources

- [API transport tests](../../frontend/src/api.test.ts): old 401 cannot expire a new session; late body cannot return old data; browser marker contains no credentials.
- [Session tests](../../frontend/src/session.test.tsx): remote account change clears the workspace; a late bootstrap cannot restore it.
- [Polling tests](../../frontend/src/polling.test.tsx): terminal 401/403/404 stop retries; no overlap; unmount aborts a pending customer poll.
- [Browser account-switch tests](../../frontend/e2e/session-switch.spec.ts): same-page account switch and staff reply readback; two tabs sharing the real cookie, original workspace removal, and observation beyond two poll intervals.
- [Original browser workflows](../../frontend/e2e/workflows.spec.ts): customer/staff handoff, order actions/return review, admin controls and mobile layout.

Browser tests use a fresh isolated SQLite database and port 8001, real built assets and real API endpoints, offline generation and TF-IDF retrieval. They do not modify the user's port-8000 application or database. Headless browser automation is not a claim that an independent human tested every flow.

## Limits and follow-up

An already-sent HTTP request may reach the backend before cancellation; the guarantee is that the obsolete client stops scheduling requests and ignores old responses. Cross-tab invalidation uses the same-origin storage event and requires browser storage support. Separate profiles keep independent sessions.

During pre-fix investigation, a noisy policy question in TF-IDF mode retrieved a shipping source instead of the intended returns source. The session tests use canonical questions to isolate this lifecycle defect. This patch does not improve retrieval relevance or establish broad natural-language accuracy; the earlier AI evaluation limitations still apply.
