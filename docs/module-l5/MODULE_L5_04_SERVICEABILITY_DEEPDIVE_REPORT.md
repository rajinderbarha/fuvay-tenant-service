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

## 5b. Systemic audit — the `tenant_owner`-only isolation anti-pattern across engines

After finding this pattern twice (catalog, serviceability), I audited the whole `app/engines`
tree for role-allowlist tenant-isolation checks. Triage of every `actor_role == "tenant_owner"`
isolation site:

| Site | Verdict | Reachable by staff/tech? | Action |
|---|---|---|---|
| `serviceability/_assert_owns_tenant` | **ACTIVE IDOR** | yes (`tenant_service_area:read`) | fixed (§2-3) |
| `booking/_assert_can_access_booking` | **ACTIVE IDOR (customer PII)** | yes (`booking:bookings:read`) | **fixed (below)** |
| `booking.list_bookings` `else` branch | **ACTIVE (cross-tenant list)** | yes | **fixed (below)** |
| `admin_catalog/_assert_tenant_owns_ts` | defense-in-depth | no (lacks `tenant:*`) | fixed earlier (03 slice) |
| `platform_commerce/_assert_owns_tenant_deposit` | defense-in-depth | no (deposit perms platform-only) | **hardened (below)** |
| `field_ops/*` (`_assert_can_access_job` etc.) | **SECURE** | n/a | not changed — uses `_assert_assigned` (staff/tech confined to jobs *assigned to them*, stricter than tenant) |
| `serviceability/_assert_admin_can_view_customer` | **SECURE** | n/a | positive allowlist + fail-closed default `raise`; only tenant_owner holds perm |
| `serviceability` matching `filter_tenant` | **SECURE** | n/a | marketplace matching (None = all serving tenants, correct for customers) |
| `platform_notifications` recipient query | **SECURE** | n/a | a SELECT filter, not an isolation check |

### 5b.1 Booking — ACTIVE cross-tenant customer-PII IDOR (HIGH, most severe of the session)

`P.BOOKING_READ` = `booking:bookings:read`, held by **staff and technician**.
`GET /v1/bookings/{booking_id}` → `get_booking` → `_assert_can_access_booking`, which handled
only `customer` and `tenant_owner` and **fell through with no check** for staff/technician. So a
staff/technician at tenant A could read **any booking across all tenants** — customer name,
address, phone, schedule, price. `list_bookings` similarly let them fall into an `else` branch
that accepted an arbitrary `tenant_id`, listing any tenant's bookings.

**Fixed:** `_assert_can_access_booking` is now fail-closed — platform roles unrestricted;
`customer` → own booking; every other (tenant-scoped) role → own tenant; no-tenant/guest →
denied. `list_bookings` forces tenant scoping for all tenant-scoped roles and only lets platform
roles filter by arbitrary tenant/customer. A stale test
(`test_customer_idor.py::test_staff_can_view_any_booking_in_their_tenant`) that had **encoded
the vulnerability** (staff with no tenant_id viewing any booking) was corrected to assert the
secure behavior (own-tenant allowed, other-tenant denied) + a new denial regression test.

### 5b.2 Security deposit — hardened (defense-in-depth)

`platform_commerce/_assert_owns_tenant_deposit` had the same `tenant_owner`-only gate. Deposit
perms are platform-only (`admin_finance`/`admin_readonly`), so it was not reachable by
staff/technician — hardened anyway to the PLATFORM_ROLES-denylist pattern for consistency and
future-proofing (behavior-identical for tenant_owner and platform).

### 5b.3 Systemic guard

`e2e/cross_tenant_isolation_guard.py` (fail-closed) locks in all four fixes — asserts each
audited isolation method has dropped the vulnerable `actor_role == "tenant_owner"` gate and uses
a PLATFORM_ROLES denylist. Passes (4/4). Deliberately a fixed registry, not a broad grep, so the
legitimate `tenant_owner` uses above are not flagged.

## 6. Files Changed

- `app/engines/serviceability/service.py` — `_assert_owns_tenant` hardened (active IDOR fix).
- `app/engines/booking/service.py` — `_assert_can_access_booking` + `list_bookings` fail-closed
  tenant scoping (active cross-tenant customer-PII IDOR fix).
- `app/engines/platform_commerce/service.py` — `_assert_owns_tenant_deposit` hardened (d-i-d).
- `e2e/serviceability_isolation_guard.py`, `e2e/cross_tenant_isolation_guard.py` — new guards.
- `tests/test_module_l5_04_service_area_isolation.py` (6), `tests/test_customer_idor.py`
  (corrected stale test + new denial regression) — tests.
- `docs/module-l5/MODULE_L5_04_SERVICEABILITY_DEEPDIVE_REPORT.md` — this report.

## 7. Honest Status

Tenant service-area cross-tenant isolation: **active IDOR fixed, guarded, tested.** Genuine
security improvement. Full MODULE-L5-04 `PROVEN_LEVEL_5` not claimed — the broader Region &
Serviceability surface (geography hierarchy, zone/zipcode coverage, tier mapping, matching-engine
integration, frontend completion) remains a scoped multi-pass effort.
