# MODULE-L5-05 — Booking & Preflight: High-Value Deep-Dive (Mutation Isolation)

## 1. Scope & Status

**Deep-dive slice** continuing from the MODULE-L5-04 booking *read* IDOR fix into booking
**mutation** authorization. Found and fixed a class of **cross-tenant mutation IDORs** where
booking-modifying methods loaded a booking by ID and mutated it with no tenant/customer scope
check. Not a full-module PROVEN_LEVEL_5 claim.

## 2. Central Finding — cross-tenant booking mutation IDOR class

After MODULE-L5-04 fixed booking *read* isolation (`_assert_can_access_booking`), I audited every
`BookingService` method that loads a booking by ID. Five **mutation** methods loaded a booking (or
its reschedule request) and mutated it **without** calling the access check:

| Method | Endpoint auth | Reachable by | Severity |
|---|---|---|---|
| `add_note` | `get_current_user` (**auth-only, no permission**) | **any authenticated user** | **HIGH** — any logged-in user could inject a note (incl. `is_internal`) into any tenant's booking |
| `request_reschedule` | `BOOKING_RESCHEDULE` | `tenant_owner` (+ customer, who *was* scoped via `_assert_owns`) | HIGH — tenant_owner could reschedule another tenant's booking |
| `accept_reschedule` | `TENANT_UPDATE` | `tenant_owner` | HIGH — accept another tenant's reschedule |
| `reject_reschedule` | `TENANT_UPDATE` | `tenant_owner` | HIGH — reject another tenant's reschedule (didn't even load the booking) |
| `void_booking` | `require_super_admin` | super_admin only | none (platform-only) — hardened for defense-in-depth |

`add_note` is the most severe: its endpoint had **no permission check at all** (only
`Depends(get_current_user)`), and the service method had no scope check — so any authenticated
user (any role, any tenant, even a customer or token-holding guest) could add notes, including
internal notes, to **any** booking across all tenants.

## 3. Fix

Every booking-mutation method that loads a booking now calls
`self._assert_can_access_booking(b)` (the canonical fail-closed isolation check from
MODULE-L5-04: platform roles unrestricted; customer → own booking; every other tenant-scoped
role → own tenant; no-tenant/guest → denied):

- `request_reschedule`: replaced the customer-only `_assert_owns(b.customer_id)` with
  `_assert_can_access_booking(b)` (covers customer AND tenant scoping).
- `accept_reschedule`: added the check after loading the booking from the reschedule request.
- `reject_reschedule`: now loads the booking from `req.booking_id` and asserts (was unscoped).
- `add_note`: added the check (closes the any-user cross-tenant note injection).
- `void_booking`: added the check (defense-in-depth; super_admin exempt).

**Note (not blocking):** `add_note`'s endpoint remains `get_current_user` (auth-only). The
service-level `_assert_can_access_booking` now confines it to the booking's tenant/owner, which
closes the cross-tenant hole; adding an explicit endpoint permission would be a further
hardening (recorded, not done this slice).

## 4. Verification

- **4 tests** (`tests/test_module_l5_05_booking_mutation_isolation.py`): add_note cross-tenant
  blocked, add_note own-tenant allowed, tenant_owner cross-tenant mutation blocked, guard
  enforces coverage.
- **Systemic guard extended** (`e2e/cross_tenant_isolation_guard.py`): new
  booking-mutation-coverage check — every `BookingService` method that loads a `Booking` by id
  MUST call `_assert_can_access_booking` (allowlisting only `create_booking`, which re-fetches
  solely via the actor's own Redis idempotency key). Fails closed on any new unscoped
  booking-by-id method.
- **332 booking/reschedule/idor tests pass**; full regression (totals in commit) — no
  sprint-attributable regression.

## 5. Files Changed

- `app/engines/booking/service.py` — 5 mutation methods now enforce `_assert_can_access_booking`.
- `e2e/cross_tenant_isolation_guard.py` — booking-mutation-coverage check.
- `tests/test_module_l5_05_booking_mutation_isolation.py` — new tests (4).
- `docs/module-l5/MODULE_L5_05_BOOKING_MUTATION_DEEPDIVE_REPORT.md` — this report.

## 6. Honest Status

Booking mutation cross-tenant isolation: **IDOR class fixed, guarded, tested.** Combined with the
MODULE-L5-04 read fix, the booking access surface (read + the audited mutations) is now
consistently tenant-confined and regression-guarded. Full MODULE-L5-05 `PROVEN_LEVEL_5` not
claimed — the broader Booking & Preflight surface (preflight validation, slot/availability
integrity, quote/inspection integration, state machine, frontend) remains a scoped multi-pass
effort.
