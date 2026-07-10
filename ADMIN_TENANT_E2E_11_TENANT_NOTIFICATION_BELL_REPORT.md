# ADMIN-TENANT-E2E-11 — Tenant Notification Bell Report

## Real bug found and fixed this pass
The topbar bell (`components/layout/TenantLayout.tsx`) was a plain
`<button>` with **no `onClick` at all** — clicking it did nothing. This
is the exact same dead-bell pattern found and fixed on the admin side in
E2E-06B.

**Fixed**: changed to an `<a href="/notifications" aria-label="Notifications">`,
matching the established fix pattern.

## Checks
1. Bell visible — confirmed.
2. Bell count real — no fake badge exists or was added; this
   notification model has no unread/read concept (see notifications
   report), so no count is shown at all — an honest absence, not a fake
   zero or a fabricated number.
3. Bell opens `/tenant/notifications` — confirmed, browser-verified,
   real navigation on click.
4. No fake unread badge — confirmed, none exists.
5. No route confusion — confirmed, single unambiguous destination.

## Verdict
Real bug fixed, browser-verified working.
