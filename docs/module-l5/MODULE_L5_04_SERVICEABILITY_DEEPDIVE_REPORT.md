# MODULE-L5-04 — Region & Serviceability: High-Value Deep-Dive (Tenant Service-Area Isolation)

## 1. Scope & Status

**Deep-dive slice** on the highest-risk Region & Serviceability area: cross-tenant isolation of
tenant service areas. Found and fixed a genuine **ACTIVE HIGH-severity cross-tenant read IDOR**;
added a fail-closed guard + tests; verified two adjacent `actor_role == "tenant_owner"` sites are
legitimate (not bugs). Not a full-module PROVEN_LEVEL_5 claim.

## 2. Central Finding — ACTIVE cross-tenant service-area read IDOR (HIGH)

`app/engines/serviceability/service.py::_assert_owns_tenant` — the single isolation control that
every `/{area_id}` service-area/mapping method routes through (via `get_service_area` /
`_get_mapping`) — confined **only** `tenant_owner`:

```python
if self.actor_role == "tenant_owner" and (self.actor_tenant_id is None or self.actor_tenant_id != tenant_id):
    raise NotFoundException(...)
```

But `staff` and `technician` **both hold `tenant_service_area:read`** (confirmed in
`ROLE_PERMISSIONS`), and `GET /v1/tenant/service-areas/{area_id}` requires exactly
`TENANT_SERVICE_AREA_READ`. So the `tenant_owner`-only gate **failed open** for staff/technician:

**Exploit:** a `staff` or `technician` user at tenant A, using a valid `area_id` belonging to
tenant B, calls `GET /v1/tenant/service-areas/{area_id}` (and `/services`) and reads **tenant B's
service-area configuration** — cross-tenant data leak. Area UUIDs are not a security boundary
(they surface in matching results, referrals, logs). This is **active**, not merely
defense-in-depth (unlike the analogous catalog finding, where the roles lacked the permission).

## 3. Fix

`_assert_owns_tenant` now confines **every** tenant-scoped actor and exempts only platform roles:

```python
PLATFORM_ROLES = ("super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly")
def _assert_owns_tenant(self, tenant_id):
    if self.actor_role not in self.PLATFORM_ROLES:
        if self.actor_tenant_id is None or self.actor_tenant_id != tenant_id:
            raise NotFoundException("TenantServiceArea", str(tenant_id))
```

- `staff`/`technician`/`tenant_owner`/any future tenant role → confined to their own tenant
  (must have a matching `tenant_id`).
- Platform roles (`super_admin`, `admin_*`) carry `tenant_id=None` (01D-R canonical model) and
  legitimately manage any tenant via `/v1/admin/tenants/{tenant_id}/service-areas`.
- **Caller safety verified:** all callers of `get_service_area`/`_assert_owns_tenant` are within
  the serviceability service's own tenant-management methods — no matching/booking/customer/
  system flow calls it, so the stricter check breaks nothing (156 serviceability tests pass).

## 4. Adjacent sites checked — NOT bugs (verified, not changed)

- `_assert_admin_can_view_customer` (line ~176): a positive allowlist — `super_admin` allowed;
  `tenant_owner` allowed only with a booking/job for that customer in their tenant; **fail-closed
  default `raise`** for everyone else; only `tenant_owner` holds `customer_address:admin_read`.
  Secure.
- `check_serviceability` matching (line ~997): `filter_tenant = actor_tenant_id if
  tenant_owner else None` — this is **marketplace matching**; `None` = "match across all serving
  tenants," which is the correct behaviour for a customer/guest serviceability check (the same
  data customers see). Not a private-data leak.
- Line ~407: a comment. The guard is scoped to the `_assert_owns_tenant` method to avoid
  flagging these legitimate uses.

## 5. Verification

- **6 tests** (`tests/test_module_l5_04_service_area_isolation.py`): staff denied other tenant,
  technician denied, tenant_owner still confined, tenant role with no tenant denied, all 5
  platform roles exempt, guard passes.
- **Fail-closed guard** (`e2e/serviceability_isolation_guard.py`): fails if the vulnerable
  `actor_role == "tenant_owner"` gate returns to `_assert_owns_tenant`, if it stops confining via
  PLATFORM_ROLES/actor_tenant_id, or if a raw unscoped `db.get(TenantServiceArea, ...)` appears
  outside `get_service_area`.
- **156 serviceability tests pass**; full regression (totals in commit) — no sprint-attributable
  regression.

## 6. Files Changed

- `app/engines/serviceability/service.py` — `_assert_owns_tenant` hardened (active IDOR fix).
- `e2e/serviceability_isolation_guard.py` — new fail-closed guard.
- `tests/test_module_l5_04_service_area_isolation.py` — new tests (6).
- `docs/module-l5/MODULE_L5_04_SERVICEABILITY_DEEPDIVE_REPORT.md` — this report.

## 7. Honest Status

Tenant service-area cross-tenant isolation: **active IDOR fixed, guarded, tested.** Genuine
security improvement. Full MODULE-L5-04 `PROVEN_LEVEL_5` not claimed — the broader Region &
Serviceability surface (geography hierarchy, zone/zipcode coverage, tier mapping, matching-engine
integration, frontend completion) remains a scoped multi-pass effort.
