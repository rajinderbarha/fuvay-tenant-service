# Phase 1 — Admin Setup Frontend + Backend Certification — Bug Fix Report

## Bugs found this sprint

1. **Login events not exposed under `/admin/audit-logs` namespace.** Initial
   investigation found `GET /v1/admin/audit-logs?action=login` returned 0
   results, suggesting login events were invisible to admins entirely.

## Fix applied

Added `GET /v1/admin/audit-logs/login-events` to
`app/engines/platform_notifications/admin_router.py`, querying the
`login_events` table directly (email/event_type filters, `request_id`
included per row). Live-verified: returns real login/logout history with
`request_id` present.

## Correction (found during verification, not a real gap)

Further investigation revealed login events were **already** visible via a
pre-existing, separate endpoint: `GET /v1/auth/audit-log`, wired to the
frontend's "Auth Audit" tab on `/admin/audit-logs`
(`app/admin/audit-logs/page.tsx:97`). This means the original "gap" was a
false alarm caused by checking only one of **three** parallel audit-log
systems in this codebase (`platform_audit_logs`, the platform_notifications
engine-audit table, and this `login_events`/`/v1/auth/audit-log` system).

This sprint's new endpoint is therefore **not fixing a missing capability**
— it's a harmless, additive convenience route (login events now reachable
under both `/v1/auth/audit-log` and `/v1/admin/audit-logs/login-events`).
Documented honestly rather than overclaiming a bug fix that wasn't actually
necessary. The real, still-open finding is the **existence of three parallel
audit systems** with no consolidation — carried forward as a blocker (see
`PHASE_1_ADMIN_SETUP_REMAINING_BLOCKERS.md`), same as flagged in the earlier
DPDP compliance and Admin Setup certification sprints this session.

## No other bugs found this sprint

Every other Phase 1 module (auth, dashboard shell, platform settings,
navigation, engine management, vertical configuration, error/request_id
envelopes, Swagger coverage) was already correct — largely because the
earlier Phase 1 (Admin Setup Certification) sprint in this same session
already found and fixed the one real defect that existed
(platform-settings value-type validation), and Phase 0's cleanup/reseed
didn't introduce new backend defects in this module surface.
