# ADMIN-TENANT-E2E-06 — Delivery Logs Report

## Route: `/admin/notification-outbox` (not `/admin/notifications/delivery-logs`)

## Live-verified backend
`GET /v1/admin/notification-outbox?limit=5` → `200`,
`{"items": [], "total": 0, "limit": 5, "offset": 0}` — honest empty
state (no notifications have been dispatched through the outbox for
this dev environment yet).

`retryOutbox(id)` client method exists
(`POST /v1/admin/notification-outbox/{id}/retry`) — not live-tested
since no outbox rows exist to retry against.

## Verdict
Delivery Logs: **route real (as "outbox"), backend real, honest empty
state.** Retry action exists in the API client but wasn't exercised
(no real failed delivery exists in this dev environment to retry).
