# GeoService Authorization Context (WS9)

## The problem

Prior to this slice, `GeoService` took only `db`/`request_id`/`actor_id`/
`actor_role`. `delete_zone` had no tenant argument at all;
`create_zone`/`update_staff_location` took a `tenant_id` argument but
trusted it unconditionally — a route guard proves the caller has a
permission bit, not which tenant's data they may touch.

## The fix

`GeoService.__init__` now accepts `actor_tenant_id: uuid.UUID | None`,
supplied by the router's `_svc()` dependency from `UserContext.tenant_id`
(never from the client body/path). A new helper,
`_require_trusted_tenant(requested_tenant_id=None)`:

- Returns `requested_tenant_id` unchanged for `actor_role == "super_admin"`
  (platform staff pass through, admin tooling unaffected).
- Raises `PERMISSION_DENIED` if `actor_tenant_id is None` (fail closed).
- Raises `PERMISSION_DENIED` if a `requested_tenant_id` was supplied and
  doesn't match `actor_tenant_id`.
- Returns `actor_tenant_id` otherwise — the single authoritative value
  every mutation scopes by.

Wired into:

- `delete_zone` — `tenant_id = self._require_trusted_tenant()` (no
  requested value — the route has none), used to scope the query.
- `create_zone` — `tenant_id = self._require_trusted_tenant(tenant_id)`,
  verifying the path value and reassigning it to the trusted value before
  the `ServiceZone` row is built.
- `update_staff_location` — same pattern, verifying the path `tenant_id`
  before the `StaffLocation` upsert.

`get_zone`/`update_zone`/`list_tenant_zones`/`check_pincode_in_zone`/
`get_staff_location`/`get_staff_in_radius`/`get_coverage_map` were **not**
touched — they are outside this slice's frozen scope (Set C or reads not
in the residual mutation set).

## Caller enumeration (fail-closed for incomplete direct calls)

`git grep GeoService(` found exactly 2 construction sites: the router's
`_svc()` (supplies full trusted context) and `app/engines/booking/
service.py`'s preflight check (constructs with `db` only, calls only the
untouched read-only `check_pincode_in_zone`). `git grep` for direct
`.delete_zone(`/`.create_zone(`/`.update_staff_location(` calls outside
`service.py`/`router.py` found matches only in `pricing/router.py` and
`location_engine/router.py` — confirmed by class-identity check
(`LocationService is not GeoService`, `PricingService is not GeoService`)
to be unrelated same-named methods on different service classes, not a
bypass.

Because `actor_tenant_id` defaults to `None`, any future direct-call site
that omits it fails closed the first time it calls `delete_zone`,
`create_zone`, or `update_staff_location` (raises `PERMISSION_DENIED: No
tenant context`) rather than silently trusting a caller-supplied value.

## Transaction/exception behavior

`_require_trusted_tenant` raises `ServiceOSException`, which is not
caught by any broad `except Exception` in the modified methods — the
Redis best-effort blocks use narrowly-scoped `try/except Exception: pass`
around ONLY the Redis calls (pre-existing pattern), never around the
authorization check or the primary DB write. Each mutation remains a
single statement within the request's existing DB session/transaction.
