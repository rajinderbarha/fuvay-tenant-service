# MediaService Authorization Context (WS4)

## The problem

Prior to this slice, `MediaService` took only `db`/`request_id`/`actor_id`.
Every mutation trusted whatever `tenant_id` argument its caller passed —
which, for all 3 `router.py` mutation routes, came straight from the
request body or URL path with **no comparison to the calling principal**.
A route guard (`get_current_user`, `require_permission`) proves the caller
is authenticated/has a permission bit; it proves nothing about which
tenant's data the caller is allowed to touch. A direct `MediaService(...)`
call — bypassing the router entirely — would have inherited the same gap.

## The fix

`MediaService.__init__` now accepts `actor_role: str | None` and
`actor_tenant_id: uuid.UUID | None`, both supplied by the router's `_svc()`
dependency from the authenticated `UserContext` (never from the client
body). A new helper, `_require_trusted_tenant(requested_tenant_id)`:

- Passes silently for `actor_role == "super_admin"` (platform staff).
- Raises `PERMISSION_DENIED` if `actor_tenant_id is None` (fail closed —
  no tenant context means no authority, not "no restriction").
- Raises the same `PERMISSION_DENIED` if `requested_tenant_id !=
  actor_tenant_id`.

Wired into:

- `initiate_upload` — first statement, before quota checks or the DB write.
- `delete_file` — first statement, before the `MediaFile` query.
- `confirm_upload` — a parallel but distinct check (no `tenant_id` argument
  exists on this endpoint at all): after loading the `MediaUploadSession`,
  the confirming principal must either own the session
  (`sess.owner_id == actor_id`) or share the session's tenant
  (`sess.tenant_id == actor_tenant_id`); otherwise the SAME
  `NotFoundException("UploadSession", ...)` is raised as for a genuinely
  missing session_id.

## Caller enumeration (fail-closed for incomplete direct calls)

`git grep` for `MediaService(` across `app/` found exactly one construction
site: `app/engines/media/router.py`'s `_svc()` dependency, which supplies
`actor_role`/`actor_tenant_id` on every call. `git grep` for
`.initiate_upload(` / `.confirm_upload(` / `.delete_file(` outside
`service.py`/`router.py` found zero call sites. There is no internal caller
to preserve via an explicit trusted-context override — the router is the
only caller, and it is now correct. See
[service-caller-graph.csv](service-caller-graph.csv) and
[internal-caller-preservation.csv](internal-caller-preservation.csv).

Because `actor_role`/`actor_tenant_id` default to `None` in `__init__`, any
future direct-call site that omits them will fail closed the first time it
calls `initiate_upload` or `delete_file` (raises `PERMISSION_DENIED: No
tenant context`) rather than silently trusting a caller-supplied
`tenant_id`. `confirm_upload`'s ownership check has the same fail-closed
property (`actor_id is None` and `actor_tenant_id is None` both evaluate
false, so `owns_session`/`same_tenant` are both false and the branch
raises).

## Negative tests

`tests/test_phase2f31a_n01_residual_closure.py::TestMediaServiceTenantAuthority`
covers: helper existence, both mutations calling it, ordering (before the
query), the explicit `super_admin` bypass, and fail-closed behavior for
`actor_tenant_id is None`.
