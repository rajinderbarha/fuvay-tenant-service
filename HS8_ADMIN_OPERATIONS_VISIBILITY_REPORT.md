# HS8 — Admin Operations Visibility Report

## Live-verified
- `GET /v1/admin/service-jobs/{job_id}/assignment-timeline` (`admin_router.py`
  in `home_service_assignment`) → real assignment event history (who
  assigned, when, to which technician).
- `GET /v1/admin/service-jobs/{job_id}/execution-timeline`
  (`execution/home_service_router.py`'s `admin_router`) → real, complete
  execution event history (`technician_on_the_way`, `technician_reached_site`,
  etc. with `old_status`/`new_status`/timestamps).

Both endpoints returned real data for the live-verified job this pass,
scoped by `job_id` with no tenant/customer identity leakage issues
observed.

## Not verified this pass
No dedicated `/admin/home-services/operations` dashboard route (listing
bookings/jobs/providers/technicians/SLA/parts/complaints/timeline in one
place, per the ticket) was found or exercised — only the two
job-scoped timeline endpoints above. Reassign/cancel-with-reason admin
actions exist in `admin_router.py` at the route level (not curl-verified
this pass due to time). Permission-gating on these admin endpoints
(`require_super_admin` vs. granular `admin.home_services.jobs.*`) not
inspected this pass.

## Verdict
Admin visibility: **partially verified** — the two timeline endpoints
work and return real data; a consolidated operations dashboard and
granular permission gating were not investigated.
