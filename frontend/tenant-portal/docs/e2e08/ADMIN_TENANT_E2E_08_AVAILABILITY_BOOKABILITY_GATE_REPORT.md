# ADMIN-TENANT-E2E-08: Availability Bookability Gate Report

**Date:** 2026-07-10

## Bookability Gate Logic (Availability)

`detectIssues()` function enforces the following checks on loaded rules:

| Check | Severity | Code |
|-------|----------|------|
| No active rules | danger | no_active_rules |
| End time <= start time | danger | invalid_time_range |
| Slot duration < 15 min | warning | slot_duration_too_small |
| Slot duration > 480 min | warning | slot_duration_too_large |
| Max bookings per slot < 1 | danger | max_bookings_missing |
| Scoped rule missing scope_id | warning | scope_id_missing |

## Status Badge
Header badge shows: "Configured" (active rules, no danger issues) / "Needs Attention" (active rules but warnings) / "Not Configured" (no active rules).

`configuredStatus = activeRules.length > 0 && issues.filter(i=>i.severity==="danger").length === 0`

## Gate: No Active Rules
When `activeRules.length === 0`, the page prominently shows:
- "No Active Rules" issue card with "Add Working Hours" CTA
- Status badge "Not Configured" (danger styling)
- Banner message: "Customers cannot book your services until you add working hours."

## Slot Preview
Client-side `generateSlots(start, end, durationMin)` generates slots visible to customers. Preview panel shows actual slots per day — helps tenants understand what customers will see before saving.

## Integration with Provider Status
`providerStatusApi.get()` is called in parallel. Its `bookability_blockers` are not surfaced in this page directly but the `is_bookable` field (via status) informs if availability is the blocking factor. Full bookability view is at `/provider/status`.
