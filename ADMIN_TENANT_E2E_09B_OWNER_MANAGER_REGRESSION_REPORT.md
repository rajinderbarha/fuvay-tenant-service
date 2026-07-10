# ADMIN-TENANT-E2E-09B — Owner/Manager Regression Report

Live API sequence run against Demo AC Services (`34b427a7-...181248`), Split AC + LG,
`tenant_service_type_id=3e00173c-...`:

1. **Baseline read (Owner)**: `GET .../type-pricing` → `tenant_min_price=850, tenant_max=1100`.
2. **Manager mutation, valid** (`900/1150`): `PUT .../pricing` → 200 OK, GET confirms
   `900/1150` persisted.
3. **Owner revert** (`850/1100`): `PUT .../pricing` → 200 OK, GET confirms original values
   restored exactly.
4. **Manager mutation, invalid** (`700/850`, below admin floor 850): → 422
   `TENANT_PRICE_BELOW_ADMIN_MIN` — real business validation still runs correctly for a
   permitted (non-read-only) actor.
5. **Service-area coverage** (`PUT /v1/provider/service-areas/{area}/coverage`) as Owner: used
   to add the new Window AC + LG coverage row for Part 8 — succeeded structurally (blocked only
   by a pre-existing DB unique constraint, see Window AC+LG report, not by the RBAC fix).
6. **Bookability check before and after all mutation testing**: `GET /v1/provider/status` as
   Owner → `is_bookable: true, is_visible: true, bookability_blockers: [], visibility_blockers:
   []` both before this sprint's testing began and after all RBAC/regression/live-matching
   tests completed.

No corruption of Demo AC Services' final state: Split AC + LG price range ends at its original
850/1100; Window AC + LG type/brand additions are new, additive, and did not touch Split AC.

Verdict: Owner and Manager mutation flows work correctly after the RBAC fix. Not
NOT_READY_TENANT_OWNER_MANAGER_MUTATION_FAILED.
