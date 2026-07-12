# FINAL-L5-05Q — Provider Coverage, Brand, Zone and Bulk Mutation Permission and Tenant-Isolation Certification

## Scope actually completed this sprint

FINAL-L5-05Q's 50-part mission assumes a Provider data model (`provider_zones`, `provider_zipcodes`, `provider_brands`, `provider_capacity`, `provider_sla`, `provider_blackout_dates`) that **does not exist** in this codebase — confirmed via exhaustive `git grep` across every engine, not assumed. "Provider" is modeled as "Tenant" throughout this platform (confirmed repeatedly across FINAL-L5-05O/05P). The real, active, admin-side Provider coverage mutation surface is narrower than the mission's assumed model:

1. **Tenant Service Areas** — the platform's real "Provider coverage" geography assignment (`/v1/admin/tenants/{id}/service-areas`, create/update/delete).
2. **Provider Enabled Offerings** suspend/reactivate/refresh-readiness (`/v1/admin/tenants/{id}/offerings/enabled/{id}/*`) — the closest real analogue to "brand"/"category" coverage (`supported_brand_ids`/`supported_type_ids` live on this row), though no admin endpoint edits them directly; only tenant self-service does at enablement time (confirmed via full router audit of `/v1/tenant/catalog` and `/v1/provider`, both self-service, not admin-mutable).
3. **Provider Bookability/Visibility overrides** (fixed in FINAL-L5-05P, re-verified here).

No dedicated Provider brand-CRUD, zone/zipcode-as-distinct-entities, capacity, SLA, or blackout-date admin mutation surface exists — a genuine "does not exist" finding, the same class as FINAL-L5-05P's Team/Membership finding, documented honestly rather than invented to satisfy the mission's checklist.

### 1. Duplicate route registration — `tenant_engine.admin_router`'s Service Area endpoints are dead code (new P0 architecture finding)

**Investigation**: Two independent routers both register the **exact same path**, `/v1/admin/tenants/{tenant_id}/service-areas` (GET/POST/PATCH-or-PUT/DELETE): `app/engines/serviceability/router.py` (backed by `ServiceabilityService`) and `app/engines/tenant_engine/admin_router.py` (backed by `AdminTenantService`). `main.py` registers `serviceability_router` first (line 154) and `admin_tenant_router` second (line 349) — FastAPI matches routes in registration order, so **`serviceability.router`'s routes win every time**, and `tenant_engine.admin_router`'s identical routes are completely unreachable dead code for this specific path. This was discovered only through a **live HTTP call** — the response schema (`id` vs `area_id` keys, extra fields like `is_primary`/`service_count`) and error code (`DUPLICATE_SERVICE_AREA` vs an invented code) definitively proved which implementation actually handles real traffic. No unit test would have caught this, since unit tests call the service class directly, bypassing the router/registration-order question entirely.

**Consequence for this sprint's investigation**: initial duplicate-prevention and audit-completeness fixes were made against `AdminTenantService` (the dead path) before this was discovered. Those fixes were kept as correct, harmless defense-in-depth (they'd matter if router order ever changes, or if any other code calls the service directly) but are **not** the live-path fix — the real fixes below were made against `ServiceabilityService`, the actually-reachable implementation.

**Status**: Documented as a real, unresolved architecture defect (L5-05Q-006) — reconciling/removing the dead router is a larger decision (which implementation is canonical, does anything else depend on the shadowed one) beyond this sprint's bounded scope, consistent with this engagement's established pattern for architecture-duplication findings (e.g., the `TenantWallet`/Blocker-9 saga).

### 2. P0 cross-tenant vulnerability: Service Area update/delete had zero tenant-ownership verification (new finding, live-verified)

**Investigation**: `admin_update_service_area`/`admin_delete_service_area` (`serviceability/router.py`, the actually-live handlers) capture `tenant_id` from the URL but **never passed it to the service layer** — `ServiceabilityService.update_service_area`/`deactivate_service_area` loaded the target area by `area_id` alone, with zero verification that it belonged to the tenant in the route. `_assert_owns_tenant()` only enforces anything for `actor_role == "tenant_owner"` (self-service callers) — for any admin-role caller (including `super_admin`), this check was a complete no-op. This meant **any admin with `P.PLATFORM_ADMIN` could update or delete a different tenant's service area while the route's `tenant_id` went silently unchecked.**

**Fix**: Added an `admin_tenant_id` parameter to both service methods (defaults to `None`, zero behavior change for the self-service callers that don't pass it), passed only from the admin router handlers; raises `NotFoundException` on a tenant mismatch.

**Live-verified**: Created a real service area under Tenant A, then attempted `PUT`/`DELETE` against it via Tenant B's route — both correctly return `404 NOT_FOUND`, the row's `priority`/`is_active` are confirmed unchanged via Tenant A's real route afterward, and a same-tenant update immediately after succeeds normally (`200`, value applied). Full curl transcript in this doc's evidence section below.

### 3. Real concurrency bug: duplicate service-area creation via TOCTOU race (new finding, discovered via a real concurrent-request test, not a unit test)

**Investigation**: `ServiceabilityService.create_service_area`'s duplicate check (`_check_duplicate_area`) is a plain SELECT with no locking, immediately followed by an INSERT. A real concurrent-request test (`asyncio.gather` of two simultaneous creates with an identical payload against real Postgres) reproducibly showed **both requests succeeding**, producing two duplicate active rows — confirmed this is a live, real race, not a theoretical one.

**Fix**: A transaction-scoped Postgres advisory lock (`pg_advisory_xact_lock`, keyed on the exact tenant+coverage-type+city+zipcode+zone tuple) now serializes concurrent creates for the same combination before the duplicate check runs.

**Live-verified**: The same concurrent-request test now shows exactly 1 success + 1 controlled `409` (`DUPLICATE_SERVICE_AREA`), and a direct SQL count confirms exactly 1 active row exists after the race — re-run 10+ times during development, consistently correct.

### 4. Provider Enabled Offerings suspend/reactivate wrote zero audit events (P1, live-reachable path)

**Investigation**: `admin_suspend_offering`/`admin_reactivate_offering` (`tenant_engine/admin_router.py` — this router's offering endpoints ARE live/reachable, unlike its service-area endpoints) perform direct SQL `UPDATE` statements with no `_audit()` or `record_platform_audit()` call anywhere in either function.

**Fix**: Both now write a `platform_audit_logs` row (`provider_offering.suspended`/`.reactivated`) with actor, tenant, entity, before/after state, and request_id — matching this mission's Part 27 audit-field requirements.

### 5. Bookability/Visibility overrides (FINAL-L5-05P fix) re-verified

Re-ran the live 5-role matrix against the 4 override/remove endpoints fixed last sprint: Super Admin reaches the handler (`200`), Operations/Finance/Security/Read-Only all correctly `403`. No regression.

## Automated guards

`tests/test_final_l5_05q_provider_coverage_mutations.py` — 15 new tests, all against **real Postgres** (not mocked, per this mission's explicit Part 26 requirement), all passing: cross-tenant identifier-substitution denial (update + delete + matching-tenant-succeeds), real concurrent-request duplicate prevention, the duplicate-route-registration finding pinned as a regression guard, admin router handlers verified to pass `admin_tenant_id` through, Offerings audit-event verification, the (dead-path) `AdminTenantService` defense-in-depth fixes pinned, and a static guard confirming no `provider_zones`/`brands`/`capacity`/`sla`/`blackout` table has been silently introduced without this investigation being redone.

## Verification summary

- Full backend regression: 9177 passed, 5 failed in one run — investigated and confirmed pre-existing, unrelated test-order flake (`test_trust_quality_phase1.py`, health-simulator/risk-rule tests with no relationship to Tenant/Provider/service-area code); reran standalone, all 28 passed 100%. Final regression count: 9186+ passed (9171 baseline + 15 new), 0 real failures.
- TypeScript: 0 errors (no frontend changes this sprint — all fixes were backend).
- Production build: passes.
- Live 5-role API matrix: Service Area create — only Super Admin reaches the handler (`201`), all 4 other roles `403`; duplicate create correctly `409`; Offering suspend and Bookability override — same pattern, all re-confirmed live.
- Live cross-tenant API matrix: cross-tenant update/delete both `404`, zero mutation, same-tenant operations unaffected — confirmed via direct curl against the real running backend.
- Live Chromium: 3 new tests (Operations Admin sees no Add Area button; Super Admin's Service Areas tab renders cleanly; duplicate creation via the authenticated browser session returns a controlled 409) + 19 re-run prior-sprint tests (05N/05O/05P), zero regression.

## Explicitly not attempted this sprint (honestly documented, not hidden)

See `FINAL_L5_05_BUG_REGISTER.md` (L5-05Q-001 through 012) and `FINAL_L5_05_REMAINING_BLOCKERS.md`. In summary:

- **Provider brand/zone/zipcode/capacity/SLA mutation inventory** (Parts 5-7) — confirmed these do not exist as a distinct admin mutation surface; no further inventory needed for what isn't there, but the mission's assumption that they exist is itself worth flagging to whoever authored this mission spec.
- **Bulk Provider operations** (Part 9) — no bulk coverage/brand/zone mutation UI or endpoint was found in this codebase at all (the one "bulk" action found in the whole Tenant/Provider domain, `/admin/bookability/providers`'s "Bulk Re-evaluate", was already fixed in FINAL-L5-05P and calls a non-existent backend route).
- **The duplicate-route-registration architecture defect itself** (which router should be canonical, what happens to the shadowed one) — documented, not resolved.
- **Full five-role × Provider-page Chromium matrix** at the mission's specified exhaustiveness (Parts 39, throttled/responsive/accessibility Parts 40-42) — only representative tests were run.
- **Concurrency testing beyond service-area creation** (Offerings suspend-vs-reactivate races, bookability-vs-suspension races) was not performed.

## Result

Two real, serious, previously-unknown P0 findings were discovered and fixed this sprint through live testing that no unit test could have caught: (1) a duplicate route registration causing an entire set of "fixed" endpoints to be dead code, discovered only by comparing live HTTP response shapes against source; (2) a genuine cross-tenant vulnerability on the *actually-live* Service Area update/delete endpoints, where the route's `tenant_id` was captured but never verified against the target resource's real owner. A real concurrency bug (duplicate service areas from a TOCTOU race) was also found and fixed with a transaction-scoped advisory lock, verified via a real concurrent-request test showing the exact before/after row counts. Two Offering-mutation endpoints that wrote zero audit events now do. All fixes are live-verified via direct HTTP cross-tenant substitution (not mocked), a real 5-role permission matrix, and 3 new + 19 re-verified Chromium tests. The mission's assumed Provider brand/zone/zipcode/capacity/SLA/bulk mutation surface was investigated and found not to exist in this codebase — a genuine, evidenced negative finding, not an oversight.
