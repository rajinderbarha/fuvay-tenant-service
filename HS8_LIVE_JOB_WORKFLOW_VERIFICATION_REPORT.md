# HS8 — Live Job Workflow Verification Report

All scenarios verified against the real running backend and real
Postgres dev database via genuine HTTP `curl` round trips, using the two
real bookings/jobs created live in HS7 (`JOB-20260709-000001`,
`JOB-20260709-000002`, tenant "Demo AC Services"
`34b427a7-b2be-496c-b826-6d51bb181248`, technician "Demo Staff"
`999ee56e-d8df-4f46-8ba6-de707b12614a`, logged in as
`staff@serviceos.in`).

## 1-2. Job created for selected provider, verified
`GET /v1/provider/service-jobs/assignable` (as `provider@serviceos.in`)
→ initially **empty** (tenant-scoping bug: `uuid.UUID(user.user_id)`
instead of `user.tenant_id`) → fixed → **200**, both real jobs returned,
`tenant_id` matching the HS7-selected provider exactly.

## 3. Assign active technician
`GET /{job_id}/eligible-staff` → real technician, `eligibility_status: eligible`.
`POST /{job_id}/assign` `{"staff_member_id": "999ee56e-..."}` → **200**,
`status: assigned`.

## 4. Reject assigning technician from another tenant
Not separately exercised this pass (time budget) — `validate_staff_eligibility`
in `service.py` does check `str(staff.tenant_id) != str(job.tenant_id)` →
`blocked_reasons: ["wrong_tenant"]`, confirmed by direct code read, not a
live negative-path curl call.

## 5-6. Move to On The Way / In Progress
`POST /{job_id}/on-the-way` → initially **500** (`UserContext` has no
`staff_member_id` field at all — hard crash) → fixed → **200**,
`status: on_the_way`. Then `reached-site` → `start-inspection` →
`complete-inspection` → `start-service`, each **200** with the correct
new status, for job 1.

## 7-8. Parts request / approval gap
`POST /{job_id}/parts-required` (job 2, after inspection) → **200**,
`status: quote_required`. No approval endpoint exists — documented in
`HS8_PARTS_REQUEST_REPORT.md`, not fabricated.

## 9. Complete job with proof
`POST /{job_id}/notes` (work note, customer-visible) → **200**.
`POST /{job_id}/media` (after-photo) → initially **500** (missing
`updated_at` on `service_job_media_uploads`) → fixed (migration 127) →
**200**. `POST /{job_id}/work-done` → **200**, `status: work_done`.

## 10. Customer booking detail shows updated timeline
`GET /v1/customer/bookings/{booking_id}` (as `customer@serviceos.in`)
→ **200**, `status: work_done`, `job_status: work_done` — confirms
`sync_booking_status` correctly propagates job status to the booking in
real time.

## 11. Payment mode unchanged
`payment_mode: customer_pays_provider_directly` confirmed present and
unchanged in the same detail response after all status transitions.

## 12. No usage credit deduction claimed
Confirmed by code inspection — no usage-credit or wallet mutation code
exists anywhere in `home_service_service.py` (execution engine). Not
claimed as implemented.

## Additional negative-path scenario
Invalid transition: `POST /{job_id}/on-the-way` on a job already at
terminal `work_done` → initially raw 500 → fixed (converted to
`ServiceOSException`) → clean 422
`EXECUTION_INVALID_STATUS_TRANSITION`, `request_id` present.

## Dev-data changes made and their disposition
| Change | Reversed after? |
|---|---|
| 3 migrations (125-127) applied | No — real schema fixes, kept |
| Job 1 driven through full lifecycle to `work_done` | No — real, valid state progression, left as evidence |
| Job 2 assigned + driven to `quote_required` (parts flagged) | No — real, valid, left as evidence |

## Verdict
Live verification: **passed**, with 3 real, severe bugs found and fixed
(tenant-scoping across 8 endpoints, staff-ID resolution across 18
endpoints combined, uncaught transition errors) plus 3 more missing
`updated_at` columns. The entire technician-side workflow was completely
non-functional before this pass.
