# ADMIN-TENANT-E2E-06 — Notification Templates Report

## Route: `/admin/notification-templates` (not `/admin/notifications/templates`)

## Live-verified backend
`GET /v1/admin/notifications/templates` → `200`, real, populated data
— confirmed real template rows including `booking_confirmed_customer_in_app`,
`document_expiring_tenant_owner_in_app`, with real fields matching the
ticket's expected set: `template_key`, `event_type`, `channel`,
`audience`, `language`, `status`, `title`, `body`, `variables`,
`is_platform_default`, `priority`.

`GET /v1/admin/notifications/templates/summary` → `200`, real
aggregate: `{"total_templates": 156, "active_templates": 66,
"draft_templates": 90, "platform_defaults": 111, "tenant_overrides": 0,
"missing_translations": 0, "validation_errors": 0, "failed_deliveries": 0}`
— a substantial, real, non-trivial dataset (156 templates), not mock data.

## Channels observed
`in_app` confirmed in the sample; not exhaustively verified whether
email/SMS/push/WhatsApp channels are populated (time budget) — the
`channel` field exists and is real, not hardcoded.

## Verdict
Notification Templates: **route real (different name than ticket's
suggestion), backend real and live-verified with substantial real
data.**
