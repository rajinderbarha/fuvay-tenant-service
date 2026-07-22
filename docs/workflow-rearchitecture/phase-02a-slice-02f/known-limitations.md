# Known Limitations — Slice 2F

1. **175 of 185 tenant-facing mutation endpoints remain without access-scope-aware protection** — the central, quantified finding of this slice, not closed.
2. **83 of those 175 show no detected route-level role/permission dependency at all** — some of these (confirmed for `execution.home_service_router`'s technician endpoints) have real in-handler/service-layer ownership checks instead, which an automated route-dependency scan cannot see; others were not individually verified and may have a genuine gap. This distinction was not resolved for all 83.
3. **`deactivate_staff` has the identical Redis-flag session-revocation gap** this slice fixed for `update_permissions` — not fixed here, flagged as a cheap, clear follow-up.
4. **Refresh-token invalidation was not separately implemented** — relies on the existing refresh-path's `session.revoked_at` check, reasoned to be sufficient but not independently re-executed against a live server this slice.
5. **Redis failure during a permission reduction fails open (logged, not raised)** — consistent with the codebase's existing pattern elsewhere, but means a Redis outage at the exact moment of a permission reduction leaves only the DB-side revocation in effect until the access token naturally expires.
6. **The job-execution/field_ops alternate-route overlap was identified but not resolved** — whether `execution.home_service_router` or `home_service_assignment.staff_router`/`provider_router` is the true canonical path for overlapping endpoints (e.g. both defining `.../accept`) was not re-adjudicated this slice.
7. **A full-repository test run was not completed** (same limitation as Slice 2E) — the 365-test targeted combined suite is the evidence base, explicitly not claimed as full-repository verification.
8. **Per-endpoint domain/record-type/ownership-mechanism columns in `tenant-mutation-endpoint-inventory.csv` are populated from automated data only** — not individually hand-verified for all 185 rows.
9. **Pre-existing duplicate-operation-ID warnings** in `service_setup/templates_router.py` remain, unrelated, not fixed (same as every prior slice).
