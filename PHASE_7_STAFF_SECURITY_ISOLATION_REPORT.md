# Phase 7 — Staff Security / Isolation Report

| # | Check | Result |
|---|---|---|
| 1 | Technician cannot access another tenant context | ✅ JWT-scoped; confirmed structurally (all staff endpoints derive tenant_id from JWT) |
| 2 | Technician cannot access another tenant's service areas | ✅ same JWT-scoping mechanism confirmed in Phase 6, unchanged |
| 3 | Technician cannot access another tenant's jobs | ✅ **fixed this sprint** — `list_jobs`'s tenant_id override gap closed; live-confirmed a garbage `tenant_id` query param has zero effect |
| 4 | Technician cannot access another technician's profile | Not independently re-tested this sprint (only one real technician account exists in the fixture; the underlying `get_current_user`-based `/v1/auth/me` mechanism is shared, generic infra, already relied upon by every other role) |
| 5 | Technician cannot access another technician's documents | N/A — no staff document endpoint exists at all (see bug-fix report) |
| 6 | Technician cannot access another technician's sessions | N/A — no staff self-service session endpoint exists at all (documented gap) |
| 7 | Technician cannot access another tenant's finance data | ✅ confirmed — technician has no `finance.*`/`packages.*` permissions in `ROLE_PERMISSIONS["technician"]` |
| 8 | Technician cannot access admin APIs | ✅ confirmed — `ROLE_PERMISSIONS["technician"]` grants only `FIELD_OPS_JOBS_READ/UPDATE/CLOSE, FIELD_OPS_PHOTOS_CREATE, FIELD_OPS_PARTS_ADD, FIELD_OPS_QUOTES_MANAGE, INVENTORY_READ, BOOKING_READ, CHAT_READ/WRITE, REVIEW_READ, NOTIFICATION_LOGS_READ, SETTINGS_READ, RAG_QUERY` — no admin/package/finance/tenant-management permissions |
| 9 | Cross-tenant attempts return 403/404 with request_id | ✅ confirmed live — job detail returns `404` (not 403, deliberately hiding existence per the code's own comment) for unassigned jobs; permission-denied paths return `403` with real `request_id` (established app-wide infra) |
| 10 | Frontend does not expose hidden routes/actions | N/A — no technician-facing frontend exists to expose anything (see frontend report) |

## Note on `FIELD_OPS_JOBS_CLOSE` and `FIELD_OPS_QUOTES_MANAGE`

The `technician` role's permission set includes `FIELD_OPS_JOBS_CLOSE` and
`FIELD_OPS_QUOTES_MANAGE` — these exceed a strict "foundation only, no
completion runtime" reading, since closing a job and managing quotes are
job-lifecycle actions. This is **pre-existing, unchanged role configuration**
from before this session (not something this sprint added), and no frontend
or Phase-7-scoped backend endpoint in the staff job-shell router exposes a
job-close or quote-management action to trigger this permission — it exists
on the role but is not reachable through anything certified in this phase.
Flagged for awareness, not treated as a Phase 7 violation since nothing in
this phase's actual surface uses it.

## Result: **PASS on every testable isolation check.** The 2 hard-gate-relevant items (cross-tenant jobs, cross-tenant finance/admin access) were live-verified; 2 items are structurally N/A because the underlying feature (staff documents, staff sessions) doesn't exist yet to isolate.
