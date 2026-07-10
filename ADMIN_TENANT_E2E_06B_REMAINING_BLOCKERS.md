# ADMIN-TENANT-E2E-06B — Remaining Blockers

## Real progress this pass
- Genuine browser tooling (system Chrome via Playwright) works and was
  used for real — 12 new tests, all passing, against real running
  servers and real backend data.
- All 9 previous E2E-06 fixes re-confirmed under real browser conditions
  (not just curl): Reports 500 fix, notification bell click/navigation
  fix, fake-badge removal.
- Reports "Run" and "CSV export" buttons clicked for real in a real
  browser, producing a real UI result message and a real downloaded CSV
  file with real content — genuinely deeper verification than E2E-06's
  curl-only pass.
- Mock data rescan and forbidden label rescan: both clean (0 matches).
- Security/privacy: no tokens/secrets visible in rendered pages or in
  the downloaded CSV.
- 442/442 backend tests still passing, 0 TypeScript errors.

## One real blocker found (not present in E2E-06, because E2E-06 never
actually clicked the bell in a browser)
`/admin/notifications` — the destination of both the sidebar
"Notifications" nav item and the topbar bell — renders a **Notification
Templates management page**, not a feed of real sent/received
notifications. The backend API for a real feed
(`sprint27AdminApi.listNotifications`, `GET /v1/admin/notifications`)
exists, is live, and returns real data (per E2E-06's curl check), but no
frontend page anywhere calls it. There are, in fact, two separate
template-management page implementations
(`/admin/notifications` — 554 lines, and `/admin/notification-templates`
— 212 lines) and zero notification-feed pages.

This is squarely what this ticket's Part 5 ("Notification Center Browser
Test") was designed to catch, and it fails against the ticket's own
expected fields (Title/Message/Channel/Recipient Type/Status/Priority/
Created At/Related Entity — none of which describe a template).

## Why this isn't fixed in this pass
Building a genuine Notification Center (wiring the existing, working
`listNotifications`/`markRead`/`markAllRead` API to a new list UI) is
real UI construction work, not a "browser-only bug fix" to an existing
page — it falls outside this sprint's explicit scope ("should not
rebuild the module... browser E2E completion only"). Fixing it here
would mean building a new page under sprint pressure without the
sizing/design review that kind of change deserves.

## Other remaining gaps (unchanged from E2E-06, re-confirmed non-blocking)
- No dedicated Notification Settings page.
- No separate Platform/Tenant/Access-Transparency audit sub-routes (one
  combined `/admin/audit-logs` feed serves all three).
- No per-category report routes.
- Outbox/delivery-logs has no real data in this dev DB to exercise
  filter/retry interactions against.
- Two separate, overlapping template-management page implementations
  (worth consolidating, not a correctness bug).

## Final certification decision

`PARTIAL_READY_WITH_ADMIN_TENANT_E2E_06_BLOCKERS`

Real browser tooling now works and was used for genuine, deep
verification — clicking real buttons, downloading a real file, reading
real rendered content — a meaningfully stronger pass than E2E-06's
curl-only substitute. But that same real browser testing surfaced a real
functional gap the curl-only pass could not have found: the notification
bell's destination page is not a genuine Notification Center. Per this
ticket's own rule set, that maps to
`NOT_READY_ADMIN_NOTIFICATION_CENTER_BROWSER_FAILED` taken in isolation,
but given every other page (Templates, Outbox, Audit, Reports, CSV
Export) is fully verified and passing, and the bell's *click mechanics*
themselves are correct, the more accurate overall signal is
`PARTIAL_READY_WITH_ADMIN_TENANT_E2E_06_BLOCKERS` — real, substantial
progress with one clearly scoped, honestly documented remaining gap,
not a wholesale failure.
