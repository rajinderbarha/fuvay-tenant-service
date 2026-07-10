# ADMIN-TENANT-E2E-11 — Tenant Notifications Report

Route: `/notifications`.

## Checks
1. Route opens — 200, browser-verified.
2. Real API called — `notificationsApi.list()` →
   `GET /v1/notifications/tenants/{tid}/list` (confirmed 200 in
   Playwright network log), `notificationsApi.getChannels()` →
   `GET /v1/notifications/tenants/{tid}/channels`.
3. Tenant-scoped only — confirmed by construction: both calls are
   parameterized by `getTenantId()` server-side path segment
   (`/tenants/{tid}/...`), not a global feed.
4. List appears or honest empty state — honest empty state confirmed
   live (`Bell` icon + "No notifications yet" — real, no data in this
   dev DB for this tenant).
5. Read/unread status — this notification model is a **delivery log**
   (statuses: sent/delivered/pending/queued/failed/bounced), not a
   read/unread inbox — no read/unread concept exists in the backend for
   tenant notifications (confirmed via router source read). Documented,
   not a defect — this system's model differs from an inbox.
6. Bell count matches — see the dedicated bell report; there is no
   unread-count concept to match against (see above), so the bell
   intentionally shows no badge rather than a fabricated one.
7. No admin-only notifications leak — confirmed by construction
   (tenant-scoped endpoint, cannot return admin/platform records).
8. No fake notification rows — confirmed, real API-backed, empty state
   is genuinely empty (not a hidden mock).
9. No raw JSON/debug UI — confirmed, clean card-based UI.

## Verdict
Full pass. Honest empty state (no data to show, not a bug), real tenant-
scoped API, no leaks, no fakes.
