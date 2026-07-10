# ADMIN-TENANT-E2E-06C: Related Entity Links Report

## Status: PARTIAL — Detail Modal Present, Deep Links Not Wired

## Current State

The `InAppNotification` type from `sprint27AdminApi` includes `notification_type` and `body` fields. The detail modal displays the full notification including type and body.

## Related Entity Linking

The notification model may include `related_entity_type` and `related_entity_id` fields depending on backend sprint 27 schema. Static analysis of the page shows the detail modal renders `n.notification_type`, `n.title`, `n.body`, `n.severity`, `n.read_status`, and timestamps.

### Deep Links by Entity Type

| Entity Type | Target Route | Status |
|---|---|---|
| Booking / Job | `/admin/bookings/{id}` | NOT_WIRED — body text only |
| Tenant | `/admin/tenants/{id}` | NOT_WIRED — body text only |
| Usage Credit Ledger | `/admin/finance/usage-credits` | NOT_WIRED |
| Report Run | `/admin/reports` | NOT_WIRED |
| Audit Event | `/admin/audit-logs` | NOT_WIRED |

## Impact

Non-blocking P2. Notifications display their full message which typically includes context. Deep links would improve UX but are not required for certification.

## Recommendation

Add `action_url` field support in a future sprint: if `n.action_url` is present, show a "View →" button that navigates to the related entity.

## Result: OUT_OF_SCOPE_FOR_NOW — does not block certification
