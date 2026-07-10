# Admin A3 — Admin Mutation Actions Report

## Actions tested (backend real, DB-backed, live-verified where noted)

| Action | Endpoint | Modal | Validation | Audit | request_id on failure |
|---|---|---|---|---|---|
| Add Usage Credits | `POST /{id}/add-usage-credits` | Yes (list+detail) | Yes | Yes (both tables, post-fix) | Yes (ServiceOSException) |
| Change Plan | `POST /{id}/change-plan` | Yes | Yes | Yes | Yes |
| Suspend Tenant | `POST /{id}/suspend` | Yes | Yes (reason required) | Yes | Yes |
| Reactivate/Unsuspend | `POST /{id}/reactivate` | Yes | Yes | Yes | Yes |
| Approve (Verify) | `POST /{id}/verify` | Yes | Yes | Yes | Yes |
| Reject | `POST /{id}/reject-verification` | Yes | Yes (reason required) | Yes | Yes |
| Adjust Security Deposit | `package_commerce` admin router | Yes | Yes | Yes | Yes |
| Add Admin Note | `POST /{id}/notes` (**new this sprint**) | **No frontend UI wired yet** | Yes (`NOTE_REQUIRED`) | Yes (reuses audit trail) | Yes |

## Real bug found and fixed this sprint
`AdminTenantService._audit()` — used by every action above — only wrote
`TenantAuditLog`, never the platform-wide `record_platform_audit()`. This
meant every one of these admin actions was invisible in the A2 Platform
Command Center's Recent Activity feed. Fixed by adding the
`record_platform_audit` call alongside the existing `TenantAuditLog`
write. Live-verified: called `/notes`, confirmed new row in
`platform_audit_logs` with `operation='admin_note_added'`, confirmed it
appeared in `GET /v1/admin/dashboard/activity-feed`.

## Live verification performed
- `POST /{id}/notes` with a test note → 200, audit row created, appeared
  in activity feed.
- `POST /{id}/change-plan` → 200, real DB row updated.
- All mutation endpoints confirmed gated by `require_super_admin`
  (coarse — see Permission Report for the fine-grained gap).

## Gap: Add Admin Note has no frontend UI
Backend method, endpoint, and `adminTenantsApi.addNote()` client method
all exist and work (curl-verified), but no button/modal was added to the
3044-line detail page's action menu this sprint. Documented in Remaining
Blockers as the one action not fully wired end-to-end.

## Verdict
7 of 8 required actions are fully wired end-to-end (modal, validation,
real API, audit, request_id-on-failure). The 8th (Add Admin Note) is
complete on the backend/API-client side only.
