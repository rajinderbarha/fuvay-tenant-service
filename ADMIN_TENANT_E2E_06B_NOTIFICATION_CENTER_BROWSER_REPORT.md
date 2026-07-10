# ADMIN-TENANT-E2E-06B — Notification Center Browser Report

## Real finding: no genuine "Notification Center" exists

The route `/admin/notifications` (`app/admin/notifications/page.tsx`,
component `NotificationTemplatesPage`, 554 lines) renders a **Notification
Templates management** UI: template list, event types, channels,
audiences, create/edit/activate template flows — using
`notifTemplateAdminApi`. This is confirmed by:
- Browser screenshot after clicking the bell: page header reads
  "Notification Templates", KPI cards read "158 TOTAL TEMPLATES / 66
  ACTIVE / 92 DRAFTS / 112 PLATFORM DEFAULTS", table columns are
  `TEMPLATE / EVENT / CHANNEL / AUDIENCE / SOURCE / STATUS / UPDATED`.
- Source inspection: no page anywhere in `app/admin/` calls
  `sprint27AdminApi.listNotifications()`, even though that method exists
  in `lib/api.ts:6679` and is fully wired to a real backend endpoint
  (`GET /v1/admin/notifications`, confirmed 200 in E2E-06 with real
  `{"items":[],"total":0}` response). It is dead/unused code.
- There is a second, separate, smaller (212-line) template page at
  `/admin/notification-templates` (`app/admin/notification-templates/page.tsx`)
  using a *different* API client (`sprint27AdminApi.listTemplates`) —
  meaning there are **two different template-management implementations**
  in the codebase, and neither route is a real notification feed.

## Against the ticket's expected fields (Title/Message/Channel/Recipient
Type/Status/Priority/Created At/Related Entity) — none of these apply to
a *template*, they describe individual *sent notification instances*,
confirming the page at this route is the wrong page for what this ticket
calls "Notification Center."

## Scope decision
Building a genuine Notification Center page (wiring the already-existing,
already-tested `listNotifications`/`markRead`/`markAllRead` API methods
to a new UI) is real, buildable work — but it is UI *construction*, not
a "browser-only bug fix" of an existing page, and this sprint's scope is
explicitly "browser E2E completion... should not rebuild the module."
Documenting honestly rather than fabricating a fix under sprint pressure.

## Verdict
**FAIL against ticket's Notification Center definition** — the route
loads (200, no crash, real data, no forbidden labels), but does not show
a feed of real sent notifications with the fields the ticket expects.
This is the primary reason full `READY` cannot be issued this pass.
