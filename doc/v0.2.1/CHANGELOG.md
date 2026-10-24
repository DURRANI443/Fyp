# Changes from v0.2.0

Date: 2026-10-24 (Asia/Karachi).

- Fixed stale customer polling after another tab changes the browser's shared account.
- Added credential-free cross-tab session invalidation and removal of stale workspaces.
- Cancelled in-flight requests and rejected responses belonging to an obsolete session, including delayed 401 and initial authentication restoration.
- Prevented overlapping customer/staff polls and stopped polling on terminal access/not-found errors.
- Added nine frontend regression cases and two real-browser account-switch workflows, retaining the original workflows.
- Rebuilt frontend assets and advanced reported application/package version to 0.2.1. No database migration or dependency changes.
- Preserved the original documentation baseline and recorded the prior browser coverage gap explicitly.
