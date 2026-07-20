# Aggregation Endpoints Implemented

## Implemented this phase

### `GET /v1/staff/my-work`
- **Router:** `app/engines/execution/my_work_router.py`
- **Service:** `app/engines/execution/my_work_service.py::TechnicianMyWorkService`
- **Reuses existing services:** No — this reads `ServiceJob` and `PartsRequest` directly via SQLAlchemy `select()`, following the exact query pattern already used by `HomeServiceJobAssignmentService.get_staff_assigned_jobs` and `HomeServiceJobExecutionService.list_parts_requests` (same filter columns: `assigned_staff_id`/`technician_id` + `tenant_id`), rather than calling into those services, to keep the read path minimal and avoid pulling in write-capable service classes for a read-only aggregation. This is a judgment call, not a strict "reuse existing services" per the letter of Workstream 12 — documented here rather than silently deviating.
- **Permissions:** `get_current_user` (standard auth dependency, same as every other endpoint in this router family).
- **Tenant scope:** enforced in both queries (`tenant_id` filter), not just in the response.
- **Partial-failure handling:** each of the two sources is wrapped independently; a failure in one does not prevent the other's data from returning (see `sources_unavailable` field).
- **Pagination:** not implemented (see `my-work-implementation.md` — judged premature for a single-technician-scoped result set).
- **Response schema:** documented via docstrings in the router/service; no separate Pydantic response model was added (the endpoint uses the same `ok()` envelope + plain dict pattern as its sibling endpoints in this router file, for consistency rather than introducing a new response-modeling convention).
- **OpenAPI description:** endpoint has a `summary`; query params have `description` text.
- **Tests:** `tests/test_phase2a_my_work.py` (13 tests).
- **Data provenance:** `ServiceJob` rows filtered by `assigned_staff_id`, `PartsRequest` rows filtered by `technician_id` — both further filtered by `tenant_id`.

## Not implemented this phase
- Admin home summary
- Business approval summary
- Provider setup progress
- Business/provider 360 summary
- My Work for any role other than technician (super_admin, tenant_owner, staff, admin_operations/finance/security/readonly)

These remain as specified in `docs/workflow-rearchitecture/phase-01/aggregation-endpoint-recommendations.md` and `docs/workflow-rearchitecture/phase-01a/phase-02-scope.md`, deferred per the narrowed vertical-slice scope for this phase.

## Explicitly not built
Booking Exception aggregation — not built, per the non-negotiable rule.
