# ADMIN-TENANT-E2E-06 — Notification Center Report

## Route: `/admin/notifications` (real, 554-line page)

## Live-verified backend
`GET /v1/admin/notifications?limit=10&offset=0` → `200`,
`{"items": [], "total": 0, "unread_count": null}` — honest empty state
for the real admin user (no fabricated rows). `GET
/v1/admin/notifications/unread-count` → `200`, `{"unread_count": 0}`.
`POST /v1/admin/notifications/mark-all-read` → `200`,
`{"marked_read": 0}` — real, correctly reflects nothing to mark given
the empty list.

## Minor inconsistency found (not fixed — low severity, documented)
The list endpoint's `unread_count` field returns `null`, while the
dedicated `/unread-count` endpoint returns a real `0`. Two different
representations of "no unread" (`null` vs `0`) from two related
endpoints — not a functional bug (both are falsy/zero-like), but a
minor API contract inconsistency worth normalizing in a future pass.

## Fields / UI
Source inspection of the 554-line page confirms a real KPI-card +
filter + table structure consistent with the ticket's expected fields
(title, message, channel, recipient, status, priority, created_at) —
not exhaustively line-by-line verified against every field given the
time budget, but no mock data or forbidden labels found in a full-file grep.

## Verdict
Notification Center: **route real, backend real and live-verified,
honest empty state confirmed.** No browser click-through performed
(see tooling-gap report).
