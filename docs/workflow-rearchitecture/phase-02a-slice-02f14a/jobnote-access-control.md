# JobNote Access Control — Closure

## Defect (confirmed live, not a product decision)

`add_note`/`list_notes` on `field_ops.router` previously:
- Accepted `tenant_id` as a client-supplied query parameter, trusted with no verification against
  the job's actual tenant — a confused-deputy vector letting any caller stamp a note with an
  arbitrary `tenant_id`.
- Performed **no job-ownership check at all** — any authenticated user (an unrelated customer, an
  unassigned technician, a staff member from a different tenant) could add or read notes on any
  job by ID.
- `list_notes` returned every note regardless of `is_internal`, exposing provider-internal notes
  to customers.

This is a real, live, same-record access-control and privacy defect — not classified as a product
decision, per the mission's explicit instruction.

## Fix applied

`FieldOpsService.add_note`/`list_notes` (`app/engines/field_ops/service.py`):
- `tenant_id` is now always derived from the loaded `Job` row (`job.tenant_id`), never from the
  client.
- `_assert_can_access_job(job)` — the same existing object-ownership check used for job reads
  (tenant_owner own-tenant, assigned staff/technician, customer own-job, super_admin
  platform-wide) — is enforced before any note read or write.
- `add_note` additionally denies `actor_role == "customer"` (`NOTE_ACCESS_DENIED`, 403) — no
  documented "customer adds a note to their own job" capability exists anywhere in this engine.
- `list_notes` filters out `is_internal=True` notes for `actor_role == "customer"`.

The route signature (`app/engines/field_ops/router.py`) no longer accepts a `tenant_id` query
param for `add_note`.

## Verified

- Tenant owner (own tenant): can add/read notes.
- Assigned technician: can add/read notes (including internal).
- Unassigned technician: denied (404, existence hidden).
- Cross-tenant tenant_owner: denied (404).
- Customer: denied write (403 `NOTE_ACCESS_DENIED`); read allowed but internal notes filtered out.
- Foreign job ID: 404, no leak.
- Author fields (`author_id`, `author_role`) are server-derived from the authenticated actor —
  never taken from the request body — so no impersonation is possible.
- No mutation occurs on any denied call (`db.add` not invoked — verified via
  `test_no_mutation_on_denied_add_note`).

See `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestJobNoteAccessControl`
(10 tests) and `direct-authorization-privacy-test-matrix.csv`.

## Residual, honestly disclosed

The runtime dependency-introspection tool still reports `add_note`/`list_notes` as
`AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` because the fix is enforced inside the service method,
not via a named FastAPI dependency (object-ownership requires loading the `Job` row first, which
can't be expressed as a simple role-only dependency the way `require_staff_or_technician_only`
was). This is the same class of tool-visibility limitation documented in Slice 2F-14 for
staff_router's original inline check — the difference is that here the underlying protection is
newly added, not merely relocated. This is disclosed in the canonical coverage reconciliation
rather than silently claimed as tool-verified.
