# Closed-Module Canary Report

Spot-checked one sample route from every previously-closed authorization
boundary to confirm none regressed as a side effect of this slice's
canonical CSV growth (297 -> 313) or matrix update:

| Closure | Sample route | Live status |
|---|---|---|
| M01 (identity/credential) | POST /v1/auth/api-keys | VERIFIED |
| N01 (media) | POST /v1/media/upload | VERIFIED |
| geo (zone management) | DELETE /v1/geo/zones/{zone_id} | VERIFIED |
| 2F-35 (critical/security batch) | DELETE /v1/webhooks/endpoints/{endpoint_id}, POST /v1/documents | VERIFIED |
| 2F-36 (enterprise/tenant-admin/operational) | POST /v1/chat/conversations/{conversation_id}/messages, PUT /v1/me/profile | VERIFIED |
| 2F-2 (provider portal) | POST /v1/provider/availability | VERIFIED |
| 2F-15C (booking lifecycle) | POST /v1/bookings/{booking_id}/confirm | VERIFIED |

All confirmed via the live canonical CSV and the full regression suite
(including every prior slice's own non-regression suite), run twice for
determinism — see `regression-report.md` for the exact final count.
