# JobMedia Access Control — Closure

## Defect (confirmed live)

Identical class of defect to JobNote: `add_media`/`list_media` accepted a client-supplied
`tenant_id` query param and performed no job-ownership check at all — any authenticated user
could attach or read media on any job by ID, regardless of tenant, assignment, or customer
relationship.

## Fix applied

`FieldOpsService.add_media`/`list_media`:
- `tenant_id` now always derived from `job.tenant_id`.
- `_assert_can_access_job(job)` enforced before any media read or write.
- `add_media` denies `actor_role == "customer"` (`MEDIA_ACCESS_DENIED`, 403) — no documented
  "customer attaches media to their own job" capability exists.
- The route no longer accepts a `tenant_id` query param.

No new upload/file/signature infrastructure was built — this only closes the ownership gap on
the existing `storage_key`-reference field (an opaque string; nothing in this codebase
dereferences it to fetch or serve a real file).

## Verified

- Assigned technician: can attach media to their own job.
- Unassigned technician: denied (404).
- Cross-tenant tenant_owner: denied (404).
- Customer: denied write (403 `MEDIA_ACCESS_DENIED`).
- Foreign job ID: 404, no leak.
- No mutation occurs on a denied call.

See `TestJobMediaAccessControl` in `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py`
(7 tests).

## Known limitation — NOT invented, honestly disclosed

`JobMedia` has **no `is_internal`-equivalent column** (unlike `JobNote`). There is therefore no
existing internal/customer-visible distinction to enforce at the row level for `list_media` — any
actor who can access the job at all (including a customer, per `_assert_can_access_job`'s
customer-own-job branch) sees all of its media. Per the mission's explicit instruction not to
build new media infrastructure, no new column/migration was added to invent this distinction.
This is recorded as `PRODUCT_DECISION_REQUIRED` in `product-decisions-required.md`, not silently
assumed as already correct, and not fixed with an invented schema change.

## Foreign/arbitrary media reference

`add_media`'s optional `media_id` field is an opaque, unvalidated UUID reference with no FK
constraint and no lookup against any other table anywhere in this codebase (confirmed via
`evidence-media-boundary.md` from Slice 2F-14: there is no dedicated media-resolution service to
substitute a foreign reference into). It is stored as-is and never dereferenced to serve content,
so "foreign media reference substitution" has no exploitable effect in the current schema — there
is nothing to substitute into. This is disclosed rather than assumed safe by omission.
